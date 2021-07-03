FROM node:12 AS client

WORKDIR /app

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

COPY \
  .browserslistrc \
  babel.config.js \
  declarations.d.ts \
  postcss.config.js \
  webpack.config.js \
  ./
COPY bundles bundles
RUN yarn build


FROM python:3.7

WORKDIR /app
RUN pip install django~=2.2
RUN django-admin startproject tracker_development

WORKDIR /app/tracker_development/donation-tracker
COPY \
  __init__.py \
  .flake8 \
  pyproject.toml \
  README.md \
  setup.py \
  ./
COPY tracker tracker
COPY --from=client /app/tracker tracker
RUN pip install -e .

WORKDIR /app/tracker_development
COPY docker/tracker_development /app/tracker_development/tracker_development
RUN mkdir db

RUN apt update
RUN apt install -y locales
RUN echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
RUN locale-gen en_US.UTF-8
ENV LC_ALL en_US.UTF-8

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]

