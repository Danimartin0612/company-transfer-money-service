pipeline {
  agent { label 'built-in' }

  options { timestamps(); timeout(time: 20, unit: 'MINUTES') }

  parameters {
    choice(name: 'ENV', choices: ['staging','production'], description: 'Entorno para integración')
    string(name: 'STAGING_URL', defaultValue: 'http://localhost:5000', description: 'Base URL de staging (http://host:puerto)')
    booleanParam(name: 'RUN_E2E', defaultValue: false, description: 'Ejecutar E2E (Selenium)')
  }

  environment {
    // Credenciales dummy válidas para LocalStack
    AWS_ACCESS_KEY_ID = 'test'
    AWS_SECRET_ACCESS_KEY = 'test'
    AWS_DEFAULT_REGION = 'eu-west-1'
    AWS_EC2_METADATA_DISABLED = 'true'
  }

  stages {

    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Setup Python 3.12') {
      steps {
        sh '''
          set -euxo pipefail
          python3 -V || true
          python3 -m venv .venv
          . .venv/bin/activate
          pip install --upgrade pip
          if [ -f ci/requirements.txt ]; then
            pip install -r ci/requirements.txt
          else
            pip install pytest
          fi
          # Herramienta para LocalStack
          pip install awscli-local
        '''
      }
    }

    stage('Unit tests') {
      steps {
        sh '''
          set -euxo pipefail
          . .venv/bin/activate
          mkdir -p reports
          # Excluimos integration y e2e por defecto
          pytest -m "not integration and not e2e" -n auto --junitxml=reports/junit-unit.xml service/tests
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

          # Arranca el mock de staging en segundo plano
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
          pytest -m "integration and not e2e" --junitxml=reports/junit-integration.xml service/tests
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

    stage('Start LocalStack (S3)') {
      steps {
        sh '''
          set -euxo pipefail
          # Levantar LocalStack (solo S3). Usa tu compose existente.
          docker compose -f ci/localstack/docker-compose.local.yml up -d

          # Espera práctica: probamos S3 de verdad con awslocal
          . .venv/bin/activate
          ENDPOINT=http://127.0.0.1:4566
          for i in $(seq 1 60); do
            if awslocal --endpoint-url=$ENDPOINT s3api list-buckets >/dev/null 2>&1; then
              echo "LocalStack S3 listo."
              break
            fi
            echo "Esperando LocalStack S3... ($i/60)"
            sleep 2
          done
        '''
      }
    }

    stage('Prepare LocalStack S3 (create bucket)') {
      steps {
        sh '''
          set -euxo pipefail
          . .venv/bin/activate
          ENDPOINT=http://127.0.0.1:4566
          BUCKET="company-transfer-ci-artifacts"

          if ! awslocal --endpoint-url=$ENDPOINT s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
            awslocal --endpoint-url=$ENDPOINT s3api create-bucket --bucket "$BUCKET" \
              --create-bucket-configuration LocationConstraint="${AWS_DEFAULT_REGION}"
            echo "Bucket creado: ${BUCKET}"
          else
            echo "Bucket ya existe: ${BUCKET}"
          fi

          awslocal --endpoint-url=$ENDPOINT s3 ls
        '''
      }
    }

    stage('E2E tests (Selenium)') {
      when { expression { return params.RUN_E2E } }
      steps {
        sh '''
          set -euxo pipefail
          . .venv/bin/activate

          # 1) Levanta selenium grid standalone chrome
          docker compose -f ci/selenium/docker-compose.e2e.yml up -d

          # 2) IP del contenedor selenium-e2e
          SEL_CONTAINER=selenium-e2e
          SEL_HOST=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$SEL_CONTAINER")
          echo "Selenium container IP: $SEL_HOST"

          # 3) Espera a que Selenium esté listo
          for i in $(seq 1 60); do
            if curl -sf "http://$SEL_HOST:4444/wd/hub/status" | grep -q '"ready":true'; then
              echo "Selenium is ready"
              break
            fi
            sleep 1
          done

          # 4) URL para los tests
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

    stage('Publish reports to S3 (LocalStack)') {
      steps {
        sh '''
          set -euxo pipefail
          . .venv/bin/activate
          ENDPOINT=http://127.0.0.1:4566
          REPO="company-transfer-money-service"
          BRANCH="${BRANCH_NAME:-$(git rev-parse --abbrev-ref HEAD)}"
          COMMIT="${GIT_COMMIT:-$(git rev-parse HEAD)}"
          CI_SYSTEM="jenkins"
          BUCKET="company-transfer-ci-artifacts"
          PREFIX="s3://${BUCKET}/${REPO}/${BRANCH}/${COMMIT}/${CI_SYSTEM}"

          [ -f reports/junit-unit.xml ] && awslocal --endpoint-url=$ENDPOINT s3 cp reports/junit-unit.xml "${PREFIX}/unit/junit-unit.xml" || true
          [ -f reports/junit-integration.xml ] && awslocal --endpoint-url=$ENDPOINT s3 cp reports/junit-integration.xml "${PREFIX}/integration/junit-integration.xml" || true
          [ -f reports/junit-e2e.xml ] && awslocal --endpoint-url=$ENDPOINT s3 cp reports/junit-e2e.xml "${PREFIX}/e2e/junit-e2e.xml" || true

          [ -d reports ] && awslocal --endpoint-url=$ENDPOINT s3 sync reports "${PREFIX}/reports" || true

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
          docker compose -f ci/localstack/docker-compose.local.yml down -v || true
        '''
      }
    }
  }
}
