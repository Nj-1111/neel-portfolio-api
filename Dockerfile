# AWS Lambda container image. Using a container (rather than a zip) avoids
# cross-compiling native wheels for psycopg and pydantic-core.
FROM public.ecr.aws/lambda/python:3.13

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

COPY app ${LAMBDA_TASK_ROOT}/app

# Schema creation and seeding are a deploy step, not a cold-start side effect.
ENV AUTO_BOOTSTRAP=0

CMD ["app.main.handler"]
