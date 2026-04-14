# Plan de Integracion de Ramas en dev

Este documento define el orden recomendado para revisar y fusionar las ramas abiertas del proyecto en la rama `dev`.

## Objetivo

- Evitar conflictos de dependencias entre ramas.
- Facilitar la revision tecnica por partes.
- Reducir riesgos de merge con cambios no relacionados.

## Reglas de Integracion

1. Todas las fusiones se realizan contra `dev`.
2. No hacer `push` directo a `dev` sin PR.
3. Respetar el orden de integracion descrito abajo.
4. Mantener en Draft los PR que dependan de otros PR aun no fusionados.
5. No subir artefactos locales de entrenamiento (`ml/logs/`, `ml/models/`).

## Orden Recomendado de Merge

1. `chore/docs-devops`
2. `fix/context-migration-weather`
3. `feat/music-spotify-sync`
4. `feat/ml-rl-core`
5. `feat/users-spotify-oauth`
6. `feat/interactions-domain-api`
7. `feat/interactions-commands`
8. `test/ml-and-interactions`

## Dependencias Tecnicas

- `feat/interactions-domain-api` depende de `feat/ml-rl-core`.
- `feat/interactions-commands` depende de `feat/interactions-domain-api`.
- `test/ml-and-interactions` depende de `feat/interactions-domain-api` y `feat/interactions-commands`.

## Checklist de Revision por PR

- [ ] CI en verde.
- [ ] Revision de codigo completada.
- [ ] Prueba local completada por al menos una persona del equipo.
- [ ] Sin secretos hardcodeados ni credenciales reales.
- [ ] Sin artefactos locales de entrenamiento.

## Nota para el Equipo

Si solo se quiere probar una rama de forma aislada, se puede hacer checkout de esa rama localmente.
Para validacion end-to-end, usar el orden de integracion indicado en este documento.
