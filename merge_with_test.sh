#!/bin/bash

# colors
NC='\033[0m'  # No Color
COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_BLUE='\033[0;34m'

# welcome title
echo -e "${COLOR_BLUE}Iniciando mezcla con pruebas...${NC}"

# get testing branch
TESTING=$1

# if there is no testing branch, exit
if [ -z "$TESTING" ]; then
    echo -e "${COLOR_RED}No se ha especificado la rama de pruebas\nejemplo: ./mezclar_con_pruebas.sh pruebas${NC}"
    exit 1
fi

# if there is not git repository, exit
if [ ! -d .git ]; then
    echo -e "${COLOR_RED}No existe un repositorio git en este directorio${NC}"
    exit 1
fi

# read actual branch name
DEVEL_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# if there is no branch name, exit
if [ -z "$DEVEL_BRANCH" ]; then
    echo -e "${COLOR_RED}No se ha podido obtener el nombre de la rama actual${NC}"
    exit 1
fi

echo -e "${COLOR_GREEN}Rama actual: ${DEVEL_BRANCH}${NC}"

# slice branch name from the beginning to the last dash
REQUIREMENT=${DEVEL_BRANCH%-*}
echo -e "${COLOR_GREEN}Requerimiento: ${REQUIREMENT}${NC}"

# if there is no requirement name, exit
if [ -z "$REQUIREMENT" ]; then
    echo -e "${COLOR_RED}No se ha podido obtener el nombre del requerimiento${NC}"
    exit 1
fi

# if there are local changes, abort
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${COLOR_RED}Hay cambios locales sin confirmar${NC}"
    echo "estás en la rama ${DEVEL_BRANCH}"
    exit 1
fi

# go to testing
echo -e "${COLOR_GREEN}Pasar a la rama ${TESTING}${NC}"
git checkout $TESTING

# update testing
echo -e "${COLOR_GREEN}Actualizando rama ${TESTING}${NC}"
git pull

# if there are local changes, abort
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${COLOR_RED}Hay cambios locales sin confirmar${NC}"
    echo "estás en la rama ${DEVEL_BRANCH}"
    exit 1
fi

# naming testing branch
TESTING_BRANCH="$REQUIREMENT-P"

# delete test branch
echo -e "${COLOR_GREEN}Eliminando rama ${TESTING_BRANCH}${NC}"
git branch -D $TESTING_BRANCH

# create test branch
echo -e "${COLOR_GREEN}Creando rama ${TESTING_BRANCH}${NC}"
git checkout -b $TESTING_BRANCH

# merge development branch
echo -e "${COLOR_GREEN}Mezclando rama ${DEVEL_BRANCH} con ${TESTING_BRANCH}${NC}"
git merge $DEVEL_BRANCH

# if there are local changes, abort
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${COLOR_RED}Hay cambios locales sin confirmar${NC}"
    echo "estás en la rama ${DEVEL_BRANCH}"
    exit 1
fi

# go to testing
echo -e "${COLOR_GREEN}Pasar a la rama ${TESTING}${NC}"
git checkout $TESTING

# merge test branch
echo -e "${COLOR_GREEN}Mezclando rama ${TESTING_BRANCH} con ${TESTING}${NC}"
git merge $TESTING_BRANCH

# end
echo -e "${COLOR_GREEN}Mezclado con éxito :D${NC}"

# if the -p flag is set (any position), push changes
if [[ $* == *-p* ]]; then
    echo -e "${COLOR_GREEN}Subiendo cambios a remoto${NC}"
    git push
fi

# if the -b flag is set (any position), go back to development branch
if [[ $* == *-b* ]]; then
    echo -e "${COLOR_GREEN}Volviendo a la rama ${DEVEL_BRANCH}${NC}"
    git checkout $DEVEL_BRANCH
    exit 0
fi

echo "actualmente estás en la rama ${TESTING}"
echo -e "usa ${COLOR_BLUE}git push${NC} para subir los cambios al remoto"
echo -e "usa ${COLOR_BLUE}git checkout ${DEVEL_BRANCH}${NC} para volver a tu rama de desarrollo"
