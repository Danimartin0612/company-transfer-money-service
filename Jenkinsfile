pipeline {
  agent { label 'built-in' }

  options {
    timestamps()
    ansiColor('xterm')
    timeout(time: 20, unit: 'MINUTES')
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
          pytest --junitxml=reports/junit-unit.xml
        '''
      }
      post {
        always {
          junit 'reports/junit-unit.xml'
          archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
      }
    }
  }
}
