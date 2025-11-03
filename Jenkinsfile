pipeline {
  agent { label 'built-in' }

  options { timestamps(); timeout(time: 20, unit: 'MINUTES') }

  parameters {
    choice(name: 'ENV', choices: ['staging','production'], description: 'Entorno para integración')
    string(name: 'STAGING_URL', defaultValue: 'http://localhost:5000', description: 'Base URL de staging (http://host:puerto)')
  }


  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Setup Python 3.12') {
      steps {
        sh '''
          python3 -V || true
          python3 -m venv .venv
          . .venv/bin/activate
          pip install --upgrade pip
          if [ -f ci/requirements.txt ]; then
            pip install -r ci/requirements.txt
          else
            pip install pytest
          fi
        '''
      }
    }

    stage('Unit tests') {
      steps {
        sh '''
          . .venv/bin/activate
          mkdir -p reports
          pytest -n auto --junitxml=reports/junit-unit.xml service/tests/unit
        '''
      }
      post {
        always {
          junit 'reports/junit-unit.xml'
          archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
      }
    }

    stage('Integration tests (staging)') {
      when { expression { return params.ENV == 'staging' } }
      steps {
        sh '''
          set -euxo pipefail
          . .venv/bin/activate

          # Arranca el mock de staging en sgundo plano
          uvicorn service.mock_staging.app:app --host 0.0.0.0 --port 5000 &
          echo $! > .staging.pid

          # Espera a que responda /health
          for i in $(seq 1 20); do
            if curl -sf http://localhost:5000/health >/dev/null; then
              break
            fi
            sleep 1
          done

          export BASE_URL="${STAGING_URL}"
          mkdir -p reports
          pytest --junitxml=reports/junit-integration.xml service/tests/integration
        '''
      }
      post {
        always {
          sh 'kill $(cat .staging.pid) 2>/dev/null || true'
          junit 'reports/junit-integration.xml'
          archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
      }
    }
    stage('E2E tests (Selenium)') {
      steps {
        sh '''
          set -euxo pipefail
          . .venv/bin/activate

          # 1) Levanta selenium
          docker compose -f ci/selenium/docker-compose.e2e.yml up -d

          # 2) Resuelve la IP del contenedor selenium-e2e en su red bridge
          SEL_CONTAINER=selenium-e2e
          SEL_HOST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$SEL_CONTAINER")
          echo "Selenium container IP: $SEL_HOST"

          # 3) Espera a que Selenium est listo
          for i in $(seq 1 60); do
            if curl -sf "http://$SEL_HOST:4444/wd/hub/status" | grep -q '"ready":true'; then
              echo "Selenium is ready"
              break
            fi
            sleep 1
          done

          # 4) Exporta la URL para los tsts
          export SELENIUM_URL="http://$SEL_HOST:4444/wd/hub"

          # 5) Ejecuta los E2E
          mkdir -p reports
          pytest -m e2e --junitxml=reports/junit-e2e.xml service/tests/e2e
        '''
      }
      post {
        always {
          sh 'docker compose -f ci/selenium/docker-compose.e2e.yml down -v || true'
          junit 'reports/junit-e2e.xml'
          archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
      }
    }
    stage('Start LocalStack (S3)') {
      steps {
        sh '''
          set -euxo pipefail
          docker compose -f ci/localstack/docker-compose.localstack.yml up -d
          # Espera a que responda
          for i in $(seq 1 30); do
            curl -sf http://localhost:4566/health | grep -q '"s3": "running"' && break || sleep 1
          done
          python -m pip install --upgrade pip awscli-local || pip install --upgrade pip awscli-local
          # Crea bucket si no existe
          awslocal --endpoint-url=http://localhost:4566 s3api head-bucket --bucket company-transfer-ci-artifacts \
            || awslocal --endpoint-url=http://localhost:4566 s3api create-bucket --bucket company-transfer-ci-artifacts
        '''
      }
    }

    stage('Publish reports to S3 (LocalStack)') {
      steps {
        sh '''
          set -euxo pipefail
          . .venv/bin/activate || true
          command -v awslocal >/dev/null 2>&1 || python -m pip install awscli-local

          REPO="company-transfer-money-service"
          BRANCH="${BRANCH_NAME:-$(git rev-parse --abbrev-ref HEAD)}"
          COMMIT="${GIT_COMMIT:-$(git rev-parse HEAD)}"
          CI_SYSTEM="jenkins"
          BUCKET="company-transfer-ci-artifacts"
          PREFIX="s3://${BUCKET}/${REPO}/${BRANCH}/${COMMIT}/${CI_SYSTEM}"

          # Sube XMLs individuales si existen
          [ -f reports/junit-unit.xml ] && awslocal s3 cp reports/junit-unit.xml "${PREFIX}/unit/junit-unit.xml" || true
          [ -f reports/junit-integration.xml ] && awslocal s3 cp reports/junit-integration.xml "${PREFIX}/integration/junit-integration.xml" || true
          [ -f reports/junit-e2e.xml ] && awslocal s3 cp reports/junit-e2e.xml "${PREFIX}/e2e/junit-e2e.xml" || true

          # Y/o todo el folder reports (screenshots, coverage, etc.)
          [ -d reports ] && awslocal s3 sync reports "${PREFIX}/reports" || true

          echo "S3_LOCALSTACK_PREFIX=${PREFIX}" | tee s3_prefix.env
        '''
      }
      post {
        always {
          script {
            def prefix = sh(returnStdout: true, script: "grep S3_LOCALSTACK_PREFIX s3_prefix.env | cut -d= -f2 || true").trim()
            if (prefix) {
              currentBuild.description = "Reports (LocalStack): ${prefix}"
              echo "Reports publicados en LocalStack: ${prefix}"
            }
          }
        }
      }
    }

    stage('Stop LocalStack') {
      steps {
        sh '''
          set -euxo pipefail
          docker compose -f ci/localstack/docker-compose.localstack.yml down -v || true
        '''
      }
    }
  }
}
