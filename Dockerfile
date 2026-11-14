# Air Check in a container: the same commands as on a laptop or in GitHub Actions.
#   docker build -t air-check .
#   docker run --rm -v "$PWD:/work" -e AIRCHECK_ROOT=/work air-check run
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY aircheck ./aircheck
COPY docs/evidence/A1_protokol_prognozy.md ./docs/evidence/A1_protokol_prognozy.md
RUN pip install --no-cache-dir .
ENTRYPOINT ["python", "-m", "aircheck"]
CMD ["selftest"]
