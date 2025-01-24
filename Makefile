IMAGE_NAME=debater
TAG=latest
REGION=asia-northeast1

LOCAL_CHAILIT_PORT=8001
REPOSITORY=debater

include .env
export $(shell sed 's/=.*//' .env)

run:
	echo $(GOOGLE_API_KEY)
	echo $(GOOGLE_SEARCH_ENGINE_ID)
	echo $(GCP_API_KEY)
	echo $(GOOGLE_APPLICATION_CREDENTIALS)
	echo $(PROJECT_ID)
	echo $(CHAINLIT_AUTH_SECRET)
	echo $(CHAINLIT_USER_NAME)
	echo $(CHAINLIT_USER_PASSWORD)
	echo $(TAVILY_API_KEY)

.PHONY: gcloud
gcloud:
	curl https://sdk.cloud.google.com | bash
	## 以下に従ってパスを通す
	code ~/.zshrc
	source ~/.zshrc
# # The next line updates PATH for the Google Cloud SDK.
# source '/vscode/home/google-cloud-sdk/path.zsh.inc'

# # The next line enables bash completion for gcloud.
# source '/vscode/home/google-cloud-sdk/completion.zsh.inc'

.PHONY:docker-image
docker-image:
	# sampleイメージをamd64アーキテクチャでビルド
	docker buildx build --platform linux/amd64 -t ${IMAGE_NAME}:${TAG} --load .

.PHONY:docker-run
docker-run:
	docker run -e GOOGLE_API_KEY=${GOOGLE_API_KEY} \
	-e GOOGLE_SEARCH_ENGINE_ID=${GOOGLE_SEARCH_ENGINE_ID} \
	-e GCP_API_KEY=${GCP_API_KEY} \
	-e GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS} \
	-e PROJECT_ID=${PROJECT_ID} \
	-e CHAINLIT_AUTH_SECRET=${CHAINLIT_AUTH_SECRET} \
	-e CHAINLIT_USER_NAME=${CHAINLIT_USER_NAME} \
	-e CHAINLIT_USER_PASSWORD=${CHAINLIT_USER_PASSWORD} \
	-e TAVILY_API_KEY=${TAVILY_API_KEY} \
	-p ${LOCAL_CHAILIT_PORT}:${LOCAL_CHAILIT_PORT} \
	${IMAGE_NAME}:${TAG}


.PHOY: docker-push
docker-push:
	gcloud auth configure-docker ${REGION}-docker.pkg.dev
	docker tag ${IMAGE_NAME}:${TAG} ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}
	docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}

