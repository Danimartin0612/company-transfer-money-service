pipeline {
  agent {
    docker {
      image "danielkube/jenkins-python312:${params.PY_IMAGE_TAG}"
      args '-u root --add-host=host.docker.internal:host-gateway -v /var/run/docker.sock:/var/run/docker.sock'
      reuseNode true
    }
  }

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        skipDefaultCheckout(true)
      }

  parameters {
    choice(name: 'ENV', choices: ['staging','production'], description: 'Entorno para integración')
    string(name: 'STAGING_URL', defaultValue: 'http://localhost:5000', description: 'Base URL de staging (http://host:puerto)')
    booleanParam(name: 'RUN_E2E', defaultValue: false, description: 'Ejecutar E2E (Selenium)')
    string(name: 'PY_IMAGE_TAG', defaultValue: 'latest', description: 'Tag de la imagen danielkube/jenkins-python312')
  }

  environment {
    AWS_ACCESS_KEY_ID = 'test'
    AWS_SECRET_ACCESS_KEY = 'test'
    AWS_DEFAULT_REGION = 'eu-west-1'
    AWS_EC2_METADATA_DISABLED = 'true'
    PIP_CACHE_DIR = "${env.WORKSPACE}/.pip-cache"
  }

  stages {
    stage('Checkout') {
      steps {
        deleteDir()
        sh 'git --version'
        checkout scm
        sh 'ls -la'
      }
    }

    stage('Setup Python 3.12') {
      steps {
        sh '''
          set -eux
          which python
          python -V
          python -m venv .venv
          . .venv/bin/activate
          mkdir -p "${PIP_CACHE_DIR}"
          python -V
          pip install --upgrade pip
          if [ -f ci/requirements.txt ]; then
            PIP_CACHE_DIR="${PIP_CACHE_DIR}" pip install -r ci/requirements.txt
          else
            PIP_CACHE_DIR="${PIP_CACHE_DIR}" pip install pytest pytest-xdist requests fastapi uvicorn selenium
          fi
        '''
      }
    }

    stage('Unit tests') {
      steps {
        sh '''
          set -eux
          . .venv/bin/activate
          mkdir -p reports
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
          set -eux

          . .venv/bin/activate

          # 1) Arranca el mock de staging en background
          uvicorn service.mock_staging.app:app --host 0.0.0.0 --port 5000 &
          echo $! > .staging.pid

          # 2) Espera a que esté listo (bash/curl, sin Python heredoc)
          for i in $(seq 1 40); do
            if curl -sf "http://127.0.0.1:5000/health" >/dev/null; then
              echo "Mock listo"
              break
            fi
            sleep 1
          done

          # Si no arrancó, corta con error
          if ! curl -sf "http://127.0.0.1:5000/health" >/dev/null; then
            echo "Service did not start" >&2
            exit 1
          fi

          export BASE_URL="${STAGING_URL}"

          mkdir -p reports
          pytest -m "integration and not e2e" \
            --junitxml=reports/junit-integration.xml \
            service/tests
        '''
      }
      post {
        always {
          sh '''
            set +e
            [ -f .staging.pid ] && kill "$(cat .staging.pid)" 2>/dev/null || true
          '''
          junit 'reports/junit-integration.xml'
          archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
      }
    }

    stage('E2E tests (Selenium)') {
      when { expression { return params.RUN_E2E } }
      steps {
        sh '''
          set -eux
          . .venv/bin/activate || true

          docker compose -f ci/selenium/docker-compose.e2e.yml up -d

          SEL_BASE="http://host.docker.internal:4444"

          # Espera readiness en Selenium 4
          for i in $(seq 1 60); do
            if curl -sf "${SEL_BASE}/status" | grep -q '"ready"[[:space:]]*:[[:space:]]*true'; then
              echo "Selenium Grid READY"
              break
            fi
            sleep 1
          done

          if ! curl -sf "${SEL_BASE}/status" | grep -q '"ready"[[:space:]]*:[[:space:]]*true'; then
            echo "Selenium no levantó a tiempo" >&2
            docker compose -f ci/selenium/docker-compose.e2e.yml logs selenium || true
            exit 1
          fi

          export SELENIUM_URL="${SEL_BASE}/wd/hub"
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


    stage('Simulate S3 Upload') {
      steps {
        sh '''
          set -eux
          REPO="company-transfer-money-service"
          BRANCH="${BRANCH_NAME:-$(git rev-parse --abbrev-ref HEAD)}"
          COMMIT="${GIT_COMMIT:-$(git rev-parse HEAD)}"
          CI_SYSTEM="jenkins"
          BUCKET="company-transfer-ci-artifacts"
          PREFIX="s3://${BUCKET}/${REPO}/${BRANCH}/${COMMIT}/${CI_SYSTEM}"

          echo "=== SIMULANDO SUBIDA A S3 ==="
          mkdir -p mock-s3-upload

          for f in unit integration e2e; do
            test -f "reports/junit-$f.xml" && cp "reports/junit-$f.xml" "mock-s3-upload/junit-$f.xml" && echo "✓ junit-$f.xml"
          done
          [ -d reports ] && cp -r reports mock-s3-upload/

          echo "S3_LOCALSTACK_PREFIX=${PREFIX}" | tee s3_prefix.env

          { echo "{"; \
            echo "  \\"bucket\\": \\"${BUCKET}\\","; \
            echo "  \\"prefix\\": \\"${PREFIX}\\","; \
            echo "  \\"timestamp\\": \\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\","; \
            echo "  \\"files\\": ["; \
            first=true; \
            find mock-s3-upload -type f | while read file; do \
              if [ "$first" != "true" ]; then echo ","; fi; \
              printf '    "%s"' "${file#mock-s3-upload/}"; \
              first=false; \
            done; \
            echo ""; echo "  ]"; echo "}"; } > mock-s3-manifest.json
        '''
      }
      post {
        always {
          script {
            def prefix = sh(returnStdout: true, script: "grep S3_LOCALSTACK_PREFIX s3_prefix.env | cut -d= -f2 || true").trim()
            if (prefix) {
              currentBuild.description = "Reports (S3 Mock): ${prefix}"
              echo "Reports simulados en S3: ${prefix}"
            }
          }
          archiveArtifacts artifacts: 'mock-s3-upload/**,mock-s3-manifest.json,s3_prefix.env', allowEmptyArchive: true
        }
      }
    }
  }

  post {
    always { cleanWs() }
  }
}
