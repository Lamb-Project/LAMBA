# LAMBA - Learning Activities & Machine-Based Assessment

Actividad LTI para la entrega y evaluación de tareas educativas con feedback automatizado mediante LAMB <https://lamb-project.org>. Se integra en LMS como <https://moodle.org> vía LTI 1.1.

## Características

- 🎓 **Gestión de actividades**: Crea y administra actividades individuales o grupales
- 🤖 **Evaluación automatizada**: Integración con modelos LAMB para evaluación mediante IA
- 📝 **Entregas de estudiantes**: Sistema de entregas individuales o grupales con códigos compartidos
- 📊 **Calificaciones**: Envío automático de calificaciones a Moodle mediante LTI
- 🌐 **Multiidioma**: Soporte para catalán, español e inglés
- 🔒 **Integración LTI**: Autenticación y autorización mediante LTI 1.1

## Requisitos

- Python 3.8+
- Node.js 18+
- Moodle con soporte LTI 1.1

## Instalación

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
```

Crea un archivo `.env` basado en `env.example`:

```env
# LTI Configuration (REQUIRED)
OAUTH_CONSUMER_KEY=tu_consumer_key
LTI_SECRET=tu_secret

# Database Configuration (OPTIONAL)
DATABASE_URL=sqlite:///./lamba.db

# HTTPS Configuration for production (OPTIONAL)
HTTPS_ENABLED=false
ALLOWED_ORIGINS=*

# LAMB API Configuration (OPTIONAL)
LAMB_API_URL=http://lamb.lamb-project.org:9099
LAMB_BEARER_TOKEN=tu_token
LAMB_TIMEOUT=30

# Administrator Credentials (OPTIONAL)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
```

**Nota**: Si usas `https_server.py`, las variables `HTTPS_ENABLED` y `ALLOWED_ORIGINS` se configuran automáticamente para HTTPS. Para producción, cambia `ALLOWED_ORIGINS` a los dominios específicos permitidos.

### 2. Frontend

```bash
cd frontend/svelte-app
npm install
npm run build
```

## Ejecución

### Opción 1: HTTPS (Recomendado para producción y desarrollo con Moodle)

1. **Genera los certificados SSL** (solo la primera vez):

```bash
cd backend
python generate_ssl_cert.py
```

Esto creará los certificados autofirmados en la carpeta `backend/ssl/`:

- `cert.pem` - Certificado SSL
- `key.pem` - Clave privada

2. **Inicia el servidor HTTPS**:

```bash
python https_server.py
```

La aplicación estará disponible en:

- `https://localhost:9099` (Local)
- `https://TU_IP:9099` (Red local/Tailscale)

**Nota importante**: Al usar certificados autofirmados, tu navegador mostrará una advertencia de seguridad. Haz clic en "Avanzado" y "Proceder al sitio" para continuar. Esto es normal en entornos de desarrollo.

### Opción 2: HTTP (Solo para desarrollo local)

```bash
cd backend
python -m uvicorn main:app --reload --port 9099
```

La aplicación estará disponible en `http://localhost:9099`

**⚠️ Advertencia**: Moodle puede requerir HTTPS para la integración LTI en algunos entornos.

## Configuración en Moodle

### 1. Añadir herramienta externa LTI

1. Ve a `Administración del sitio` > `Plugins` > `Actividades` > `Herramienta externa` > `Gestionar herramientas`
2. Haz clic en `Configurar una herramienta manualmente`
3. Configura:
   - **Nombre de la herramienta**: LAMBA
   - **URL de la herramienta**: `https://tu-servidor:9099/lti` (o `https://localhost:9099/lti` para desarrollo local)
   - **Versión LTI**: LTI 1.0/1.1
   - **Clave de consumidor**: El valor de `OAUTH_CONSUMER_KEY` de tu `.env`
   - **Secreto compartido**: El valor de `LTI_SECRET` de tu `.env`
   - **Contenedor de lanzamiento predeterminado**: Nueva ventana
   - **⚠️ Importante**: Usa `https://` en la URL

4. En **Privacidad**:
   - ✅ Compartir el nombre del lanzador con la herramienta: Siempre
   - ✅ Compartir el correo del lanzador con la herramienta: Siempre
   - ✅ Aceptar calificaciones de la herramienta: Siempre

5. En **Servicios**:
   - ✅ IMS LTI Assignment and Grade Services
   - ✅ IMS LTI Names and Role Provisioning
   - ✅ Tool Settings

### 2. Crear actividades en Moodle

1. En tu curso, añade una nueva actividad de tipo **Herramienta externa**
2. Selecciona **LAMBA** como herramienta preconfigurada
3. **Importante**: El nombre de la actividad en Moodle debe coincidir con el título de la actividad en LAMBA
4. Configura las calificaciones:
   - ✅ Permitir que LAMBA añada calificaciones al libro de calificaciones
   - **Tipo de calificación**: Puntuación
   - **Calificación máxima**: 10
   - **Calificación para aprobar**: 5.00

## Estructura del proyecto

```
.
├── backend/
│   ├── main.py                   # Punto de entrada de la aplicación
│   ├── https_server.py           # Servidor HTTPS para producción
│   ├── generate_ssl_cert.py      # Script para generar certificados SSL
│   ├── config.py                 # Configuración y variables de entorno
│   ├── database.py               # Configuración de base de datos
│   ├── db_models.py              # Modelos de base de datos (SQLAlchemy)
│   ├── models.py                 # Modelos Pydantic para API
│   ├── activities_router.py      # Endpoints de actividades
│   ├── activities_service.py     # Lógica de negocio de actividades
│   ├── admin_router.py           # Endpoints de administración
│   ├── admin_service.py          # Servicio de administración
│   ├── submissions_router.py     # Endpoints de entregas
│   ├── grades_router.py          # Endpoints de calificaciones
│   ├── grade_service.py          # Servicio de calificaciones
│   ├── lti_service.py            # Servicio LTI para envío de notas
│   ├── lamb_api_service.py       # Integración con API LAMB
│   ├── storage_service.py        # Gestión de archivos subidos
│   ├── user_service.py           # Lógica de negocio de usuarios
│   ├── course_service.py         # Lógica de negocio de cursos
│   ├── moodle_service.py         # Lógica de negocio de Moodle
│   ├── document_extractor.py     # Extracción de texto de documentos
│   ├── requirements.txt          # Dependencias Python
│   ├── API_DOCUMENTATION.md      # Documentación completa de la API
│   └── ssl/                      # Certificados SSL (generados)
│
└── frontend/svelte-app/
    ├── src/
    │   ├── routes/
    │   │   ├── +page.svelte                # Página principal
    │   │   ├── +layout.svelte              # Layout raíz
    │   │   ├── +layout.js                  # Configuración de rutas
    │   │   ├── actividad/
    │   │   │   └── [activityId]/
    │   │   │       └── +page.svelte        # Vista de actividad específica
    │   │   └── admin/
    │   │       ├── +page.svelte            # Página de login admin
    │   │       ├── +layout.svelte          # Layout admin
    │   │       └── dashboard/
    │   │           ├── +page.svelte        # Dashboard principal admin
    │   │           ├── activities/         # Gestión de actividades
    │   │           ├── users/              # Gestión de usuarios
    │   │           ├── submissions/        # Gestión de entregas
    │   │           ├── grades/             # Gestión de calificaciones
    │   │           ├── courses/            # Gestión de cursos
    │   │           ├── files/              # Gestión de archivos
    │   │           └── moodle/             # Configuración Moodle
    │   ├── lib/
    │   │   ├── auth.js                     # Autenticación LTI
    │   │   ├── admin.js                    # Lógica de administración
    │   │   ├── components/
    │   │   │   ├── Nav.svelte              # Navegación principal
    │   │   │   ├── AdminNav.svelte         # Navegación admin
    │   │   │   ├── ActivityForm.svelte     # Formulario de actividades
    │   │   │   ├── DataTable.svelte        # Tabla de datos reutilizable
    │   │   │   └── LanguageSelector.svelte # Selector de idioma
    │   │   └── i18n/
    │   │       ├── index.js                # Configuración i18n
    │   │       ├── formatters.js           # Formateadores de datos
    │   │       └── locales/
    │   │           ├── ca.json             # Catalán
    │   │           ├── es.json             # Español
    │   │           └── en.json             # Inglés
    │   ├── app.html                        # HTML raíz
    │   ├── app.css                         # Estilos globales
    │   ├── app.d.ts                        # Tipos TypeScript
    │   └── tests/                          # Tests
    ├── package.json
    ├── svelte.config.js                    # Configuración Svelte
    ├── vite.config.js                      # Configuración Vite
    ├── vitest.config.js                    # Configuración Vitest
    ├── eslint.config.js                    # Configuración ESLint
    ├── jsconfig.json                       # Configuración JavaScript
    └── static/
        ├── config.js                       # Configuración frontend
        └── img/                            # Imágenes estáticas
```

## Uso

### Para administradores

1. Accede a LAMBA como administrador en `https://localhost:9099/admin`
2. Inicia sesión con las credenciales configuradas en `.env`:
   - Usuario: `ADMIN_USERNAME`
   - Contraseña: `ADMIN_PASSWORD`
3. En el panel de administración puedes:
   - **Gestionar actividades**: Ver, crear, editar y eliminar actividades
   - **Gestionar usuarios**: Ver información de usuarios registrados
   - **Ver entregas**: Monitorizar todas las entregas de estudiantes
   - **Gestionar calificaciones**: Revisar y enviar calificaciones a Moodle
   - **Configurar evaluadores LAMB**: Asociar evaluadores de IA a actividades

### Para profesores

1. Accede a LAMBA desde Moodle
2. Crea una nueva actividad especificando:
   - Título
   - Descripción
   - Tipo (individual o grupal)
   - Fecha límite (opcional)
   - ID del evaluador LAMB (opcional, para evaluación automática)
3. Los estudiantes podrán ver y entregar la actividad
4. Revisa las entregas, evalúa (manual o automáticamente) y envía las calificaciones a Moodle

### Para estudiantes

1. Accede a la actividad desde Moodle
2. Lee la descripción de la actividad
3. Sube tu documento (individual) o únete a un grupo con un código compartido
4. Espera la evaluación del profesor
5. Tu calificación se enviará automáticamente a Moodle

## Tecnologías utilizadas

### Backend

- **FastAPI**: Framework web moderno y rápido
- **SQLAlchemy**: ORM para gestión de base de datos
- **SQLite**: Base de datos (fácilmente reemplazable por PostgreSQL/MySQL)
- **Requests**: Cliente HTTP para comunicación con API LAMB
- **PyLTI**: Implementación de LTI 1.1
- **Cryptography**: Generación de certificados SSL

### Frontend

- **SvelteKit**: Framework de aplicaciones web
- **Svelte 5**: Biblioteca UI reactiva
- **Tailwind CSS**: Framework CSS utility-first
- **svelte-i18n**: Internacionalización

## Solución de problemas

### Certificados SSL

**Problema**: El navegador no confía en el certificado autofirmado

**Solución**:

1. Haz clic en "Avanzado" o "Advanced" en la advertencia del navegador
2. Selecciona "Proceder a localhost (no seguro)" o similar
3. Para Chrome/Edge: escribe `thisisunsafe` cuando veas la advertencia (sin ningún campo de texto visible)

**Alternativa**: Genera nuevos certificados si los actuales han expirado:

```bash
cd backend
python generate_ssl_cert.py
```

### Error de conexión con Moodle

**Problema**: Moodle no puede conectarse a LAMBA

**Solución**:

1. Verifica que la URL en Moodle use `https://` y el puerto correcto (9099)
2. Asegúrate de que el firewall permita conexiones al puerto 9099
3. Si usas Tailscale u otra VPN, usa la IP de la red virtual
4. Verifica que `OAUTH_CONSUMER_KEY` y `LTI_SECRET` coincidan entre Moodle y `.env`

### La evaluación automática no funciona

**Problema**: Error al evaluar con LAMB

**Solución**:

1. Verifica que `LAMB_API_URL` y `LAMB_BEARER_TOKEN` sean correctos en `.env`
2. Asegúrate de que el `evaluator_id` configurado en la actividad exista en LAMB
3. Verifica que los documentos subidos sean PDF, DOCX o TXT (formatos soportados)

### Las calificaciones no se envían a Moodle

**Problema**: Error al sincronizar calificaciones

**Solución**:

1. Verifica que la actividad en Moodle tenga activada la opción "Aceptar calificaciones de la herramienta"
2. Asegúrate de que la calificación máxima en Moodle sea 10
3. Comprueba que los estudiantes accedieron a la actividad desde Moodle (necesario para obtener `lis_result_sourcedid`)

## Documentación adicional

- **API Documentation**: Ver `backend/API_DOCUMENTATION.md` para documentación completa de todos los endpoints
- **Swagger UI**: Disponible en `https://localhost:9099/docs` cuando el servidor está corriendo
- **ReDoc**: Disponible en `https://localhost:9099/redoc` para una vista alternativa de la API

## Licencia

LAMB is licensed under the GNU General Public License v3.0 (GPL v3).

Copyright (c) 2025-2026 Arnau Tajahuerce @ArnauTajahuerce, Marc Alier @granludo (UPC), Maria José Casañ (UPC), Juanan Pereira (UPV/EHU) @juananpe

See [LICENSE](https://github.com/Lamb-Project/lamb/blob/main/LICENSE) for full details.
