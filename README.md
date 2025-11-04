# company-transfer-money-service · CI/CD

This repo ships two complementary CI setups:

* **Jenkins (declarative pipeline)** — runs in a Docker agent with Python 3.12, executes unit & integration tests, optional Selenium E2E, and simulates an S3 “publish” by generating a manifest.
* **GitHub Actions** — runs unit tests and publishes reports into **LocalStack S3** (a real S3 mock), plus uploads the reports as job artifacts.

## Repository map (relevant to CI)

```
Jenkinsfile                       # Declarative pipeline (Docker agent, stages, reports, “S3 mock”)
infra/jenkins/Dockerfile         # Jenkins controller image with Docker CLI, Git and Python 3.12
ci/requirements.txt              # Python deps for CI jobs
ci/selenium/docker-compose.e2e.yml  # Standalone Selenium Chrome for E2E
ci/localstack/docker-compose.local.yml # (optional) LocalStack compose (not used by Jenkinsfile)
```

---

## Jenkins pipeline: what it does & how it works

### Docker agent

```groovy
agent {
  docker {
    image "danielkube/jenkins-python312:${params.PY_IMAGE_TAG}"
    args '-u root --add-host=host.docker.internal:host-gateway -v /var/run/docker.sock:/var/run/docker.sock'
    reuseNode true
  }
}
```

* All stages run **inside** an agent container that already has **Python 3.12**.
* Mounts the **Docker socket** so the pipeline can launch side containers (e.g., Selenium).
* Adds `host.docker.internal` so the agent can reach services on the host.

### Parameters & environment

* `ENV` — `staging`/`production`. With `staging`, a small **uvicorn** mock is started and **integration** tests run.
* `STAGING_URL` — default `http://localhost:5000`.
* `RUN_E2E` — enable/disable Selenium E2E.
* `PY_IMAGE_TAG` — tag for `danielkube/jenkins-python312` (default `latest`).
* Env vars: dummy `AWS_*`, and `PIP_CACHE_DIR`.

### Stages

1. **Checkout**
   Cleans workspace, checks out SCM, and verifies Git runs inside the agent.

2. **Setup Python 3.12**
   Creates `.venv`, upgrades `pip`, installs `ci/requirements.txt` (or a sane default: pytest, fastapi, uvicorn, selenium…).

3. **Unit tests**

```bash
pytest -m "not integration and not e2e" -n auto --junitxml=reports/junit-unit.xml service/tests
```

Publishes `reports/junit-unit.xml` via `junit` and archives `reports/**`.

4. **Integration tests (staging only)**

* Starts: `uvicorn service.mock_staging.app:app --port 5000 &`
* Waits for `/health` (up to 40s).
* Runs:

  ```bash
  pytest -m "integration and not e2e" --junitxml=reports/junit-integration.xml service/tests
  ```
* Kills the uvicorn PID and publishes `reports/junit-integration.xml`.

5. **E2E tests (Selenium, optional)**

* `docker compose -f ci/selenium/docker-compose.e2e.yml up -d`
* Waits readiness at `http://host.docker.internal:4444/status`.
* Sets `SELENIUM_URL=http://host.docker.internal:4444/wd/hub` and runs:

  ```bash
  pytest -m e2e --junitxml=reports/junit-e2e.xml service/tests/e2e
  ```
* `docker compose down -v` and publishes the JUnit report.

6. **Simulate S3 Upload**
   Copies generated XMLs into `mock-s3-upload/` and writes **`mock-s3-manifest.json`** with `{bucket,prefix,timestamp,files}`.
   Archives: `mock-s3-upload/**`, `mock-s3-manifest.json`, `s3_prefix.env`.

> 💡 If you won’t run E2E locally, set `RUN_E2E=false` and skip Selenium entirely.

---

## Jenkins controller image (infra/jenkins/Dockerfile)

**Purpose:** a Jenkins controller image that already has:

* **Docker CLI** — lets the controller invoke `docker` and mount `/var/run/docker.sock` to agents.
* **Git** — useful for SCM and controller-level tasks.
* **Python 3.12** pre-built with a venv at `/opt/py312` (handy utilities if needed; stages still use the agent’s Python).

**Key points:**

* Base: `jenkins/jenkins:lts-jdk21`.
* Installs Docker repo & **docker-ce-cli**, plus **git**.
* Compiles **Python 3.12.7** from source (`make altinstall` so it doesn’t overwrite `/usr/bin/python3`).
* Creates venv `/opt/py312` and exports `PATH` to prioritize it.
* Switches back to `USER jenkins`.

> Typical local run (example):
>
> ```bash
> cd infra/jenkins
> docker compose up -d --build
> # Jenkins on http://localhost:8090 (mapped from 8080)
> ```

---

## GitHub Actions workflow: what it does

* Runs on `ubuntu-latest`, **Python 3.12**.
* Starts **LocalStack S3** as a service and waits for it to be healthy.
* Executes **unit tests**.
* Ensures the S3 bucket exists in LocalStack and **uploads reports** using the layout:

  ```
  s3://company-transfer-ci-artifacts/company-transfer-money-service/<branch>/<commit>/github/...
  ```
* Also uploads `reports/**` as a standard **workflow artifact**.
