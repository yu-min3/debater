IMAGE_NAME=debater
TAG=latest
REGION=asia-northeast1

LOCAL_CHAILIT_PORT=8000
REPOSITORY=debater

include .env
export $(shell sed 's/=.*//' .env)

.PHONY:docker-image
docker-image:
	# sampleイメージをamd64アーキテクチャでビルド
	docker buildx build --platform linux/amd64 -t ${IMAGE_NAME}:${TAG} --load .

.PHOY: docker-push
docker-push: docker-image
	gcloud auth configure-docker ${REGION}-docker.pkg.dev
	docker tag ${IMAGE_NAME}:${TAG} ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}
	docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}

.PHONY:docker-run
docker-run: docker-image
	docker run -it -e GOOGLE_API_KEY=${GOOGLE_API_KEY} \
	-e GOOGLE_SEARCH_ENGINE_ID=${GOOGLE_SEARCH_ENGINE_ID} \
	-e GCP_API_KEY=${GCP_API_KEY} \
	-e GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS} \
	-e PROJECT_ID=${PROJECT_ID} \
	-e TAVILY_API_KEY=${TAVILY_API_KEY} \
	-e CHAINLIT_AUTH_SECRET="${CHAINLIT_AUTH_SECRET}" \
	-e CHAINLIT_USER_NAME=${CHAINLIT_USER_NAME} \
	-e CHAINLIT_USER_PASSWORD=${CHAINLIT_USER_PASSWORD} \
	-p ${LOCAL_CHAILIT_PORT}:${LOCAL_CHAILIT_PORT} \
	${IMAGE_NAME}:${TAG}

.PHONY: serve-local
serve-local:
	uv run chainlit run app.py
