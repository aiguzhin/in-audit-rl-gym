FROM python:3.11-slim
WORKDIR /app
COPY . /app
# Зависимостей нет: только стандартная библиотека Python 3.11.
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["python", "-m", "auditenv", "check"]
