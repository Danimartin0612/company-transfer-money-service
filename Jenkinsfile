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

          # Arranca el mock de "staging" en segundo plano
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
      when { expression { return params.ENV == 'staging' } }
      steps {
        sh '''
          set -euxo pipefail
          . .venv/bin/activate

          # Levantar Selenium (standalone-chrome)
          docker compose -f ci/selenium/docker-compose.e2e.yml up -d

          # Esperar a que el hub esté listo
          for i in $(seq 1 30); do
            if curl -sf http://localhost:4444/wd/hub/status | grep -q '"ready":true'; then
              break
            fi
            sleep 1
          done

          export SELENIUM_URL="http://localhost:4444/wd/hub"
          mkdir -p reports
          pytest -m "e2e" --junitxml=reports/junit-e2e.xml service/tests/e2e
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
  }
}
