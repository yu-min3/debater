IMAGE_NAME=debater
TAG=latest
REGION=asia-northeast1

LOCAL_CHAILIT_PORT=8100
REPOSITORY=debater

include .env
export $(shell sed 's/=.*//' .env)

.PHONY: gcloud
gcloud:
	curl https://sdk.cloud.google.com | bash
	## 以下に従ってパスを通す
	code ~/.zshrc
	source ~/.zshrc
	gcloud auth login

# # The next line updates PATH for the Google Cloud SDK.
# source '/vscode/home/google-cloud-sdk/path.zsh.inc'
# # The next line enables bash completion for gcloud.
# source '/vscode/home/google-cloud-sdk/completion.zsh.inc'

.PHONY:docker-image
docker-image:
	# sampleイメージをamd64アーキテクチャでビルド
	docker buildx build --platform linux/amd64 -t ${IMAGE_NAME}:${TAG} --load .

.PHOY: docker-push
docker-push:
	gcloud auth configure-docker ${REGION}-docker.pkg.dev
	docker tag ${IMAGE_NAME}:${TAG} ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}
	docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}

# .PHONY: iap-enable
# iap-enable:
# 	gcloud compute backend-services update BACKEND_SERVICE_NAME \
#     --iap=enabled,oauth2-client-id=CLIENT_ID,oauth2-client-secret=CLIENT_SECRET \
#     --global \
#     --log-http

.PHONY:docker-run
docker-run:
	# -e CHAINLIT_AUTH_SECRET="${CHAINLIT_AUTH_SECRET}" \
	# -e CHAINLIT_USER_NAME=${CHAINLIT_USER_NAME} \
	# -e CHAINLIT_USER_PASSWORD=${CHAINLIT_USER_PASSWORD} \
	docker run -it -e GOOGLE_API_KEY=${GOOGLE_API_KEY} \
	-e GOOGLE_SEARCH_ENGINE_ID=${GOOGLE_SEARCH_ENGINE_ID} \
	-e GCP_API_KEY=${GCP_API_KEY} \
	-e GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS} \
	-e PROJECT_ID=${PROJECT_ID} \
	-e TAVILY_API_KEY=${TAVILY_API_KEY} \
	-p ${LOCAL_CHAILIT_PORT}:${LOCAL_CHAILIT_PORT} \
	${IMAGE_NAME}:${TAG}
