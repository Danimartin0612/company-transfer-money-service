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
          . .venv/bin/activate
          export BASE_URL="${STAGING_URL}"
          mkdir -p reports
          pytest --junitxml=reports/junit-integration.xml service/tests/integration
        '''
      }
      post {
        always {
          junit 'reports/junit-integration.xml'
          archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
      }
    }
  }
}
