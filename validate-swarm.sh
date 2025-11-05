# validate-swarm.sh - Validar que el despliegue fue exitoso

STACK_NAME="config-service"
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 Validando despliegue en Docker Swarm...${NC}"
echo ""

# 1. Verificar que el stack existe
echo "1️⃣  Verificando stack..."
if docker stack ls | grep -q ${STACK_NAME}; then
    echo -e "${GREEN}   ✅ Stack '${STACK_NAME}' encontrado${NC}"
else
    echo -e "${RED}   ❌ Stack '${STACK_NAME}' NO encontrado${NC}"
    exit 1
fi

# 2. Verificar servicios
echo ""
echo "2️⃣  Verificando servicios..."
docker stack services ${STACK_NAME}

# 3. Verificar réplicas
echo ""
echo "3️⃣  Verificando réplicas..."
API_REPLICAS=$(docker service ls --filter name=${STACK_NAME}_config-api --format "{{.Replicas}}")
DB_REPLICAS=$(docker service ls --filter name=${STACK_NAME}_database --format "{{.Replicas}}")

echo "   API: ${API_REPLICAS}"
echo "   DB:  ${DB_REPLICAS}"

# 4. Verificar tareas en ejecución
echo ""
echo "4️⃣  Verificando tareas..."
docker stack ps ${STACK_NAME} --no-trunc

# 5. Verificar health checks
echo ""
echo "5️⃣  Esperando health checks (30s)..."
sleep 30

# 6. Probar endpoint
echo ""
echo "6️⃣  Probando endpoint /status/..."
MANAGER_IP=$(docker node inspect self --format '{{.Status.Addr}}')
if curl -s http://${MANAGER_IP}:8000/status/ | grep -q "pong"; then
    echo -e "${GREEN}   ✅ API responde correctamente${NC}"
else
    echo -e "${RED}   ❌ API no responde${NC}"
fi

echo ""
echo -e "${BLUE}📊 Resumen del despliegue:${NC}"
echo "   Stack: ${STACK_NAME}"
echo "   API URL: http://${MANAGER_IP}:8000/docs"
echo ""
echo -e "${GREEN}✅ Validación completada!${NC}"