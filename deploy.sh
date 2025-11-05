# deploy.sh - Script de despliegue en Docker Swarm

set -e

echo "🚀 Iniciando despliegue en Docker Swarm..."

# Variables
STACK_NAME="config-service"
DOCKER_USERNAME="${DOCKER_USERNAME:-victorpabon88}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}📦 Construyendo imagen Docker...${NC}"
docker build -t ${DOCKER_USERNAME}/config-service-api:${IMAGE_TAG} .

echo -e "${BLUE}📤 Subiendo imagen a Docker Hub...${NC}"
docker push ${DOCKER_USERNAME}/config-service-api:${IMAGE_TAG}

echo -e "${BLUE}🔄 Desplegando stack en Swarm...${NC}"
export DOCKER_USERNAME=${DOCKER_USERNAME}
docker stack deploy -c compose-swarm.yml ${STACK_NAME}

echo -e "${GREEN}✅ Despliegue completado!${NC}"
echo ""
echo "📊 Para verificar el estado:"
echo "   docker stack services ${STACK_NAME}"
echo "   docker stack ps ${STACK_NAME}"
echo ""
echo "🌐 API disponible en: http://<IP_MANAGER>:8000/docs"