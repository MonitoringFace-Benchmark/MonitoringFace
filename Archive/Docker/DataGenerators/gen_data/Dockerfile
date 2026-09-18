FROM eclipse-temurin:17-jdk AS builder
RUN apt-get update && apt-get install -y git maven && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /build

ARG REPO_URL="https://git.ku.dk/krq770/monitoring_data_generator.git"
ARG GIT_BRANCH="main"
ARG GIT_COMMIT=""

RUN git clone --branch "${GIT_BRANCH}" ${REPO_URL} . \
    && if [ -n "$GIT_COMMIT" ]; then git checkout "$GIT_COMMIT"; fi
RUN mvn scala:compile compile dependency:copy-dependencies -q -DskipTests

FROM eclipse-temurin:17-jre

COPY --from=builder /build/target/classes /app/classes
COPY --from=builder /build/target/dependency /app/libs

WORKDIR /app

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["java", "-cp", "classes:libs/*", "org.entry.Dispatcher"]