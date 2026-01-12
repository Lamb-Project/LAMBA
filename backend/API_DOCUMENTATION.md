# 📚 Documentación de API - LAMBA (RESTful)

## Tabla de Contenidos
- [Introducción](#introducción)
- [Autenticación](#autenticación)
- [Endpoints LTI](#endpoints-lti)
- [Administración](#administración)
- [Actividades](#actividades)
- [Entregas (Submissions)](#entregas-submissions)
- [Calificaciones (Grades)](#calificaciones-grades)
- [Archivos Estáticos](#archivos-estáticos)
- [Códigos de Estado HTTP](#códigos-de-estado-http)
- [Modelos de Datos](#modelos-de-datos)
- [Resumen de Endpoints](#resumen-de-endpoints)
- [Flujos de Trabajo](#flujos-de-trabajo)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [Documentación Interactiva](#documentación-interactiva)
- [Mejoras RESTful Implementadas](#mejoras-restful-implementadas)
- [Notas Importantes](#notas-importantes)

---

## Introducción

Esta API sigue los principios REST:
- **Recursos** identificados por URIs claras
- **Verbos HTTP** estándar (GET, POST, PUT, DELETE)
- **Respuestas JSON** consistentes
- **Códigos de estado HTTP** semánticos

---

## Autenticación

Todos los endpoints requieren una cookie de sesión válida:
- **LTI**: `lti_session`, se establece automáticamente al acceder desde Moodle.
- **Administración**: `admin_session`, se obtiene con `POST /api/admin/login` usando `ADMIN_USERNAME` y `ADMIN_PASSWORD` (validez 24h, cookie httpOnly).

**Roles disponibles:**
- **Profesor/Admin**: `administrator`, `instructor`, `teacher`, `admin`
- **Estudiante**: `learner`, `student`

---

## Endpoints LTI

### POST `/lti`
**Descripción**: Punto de entrada LTI desde Moodle.

**Autenticación**: No requerida
**Respuesta**: Redirección HTTP 303

**Comportamiento**:
- Crea/actualiza instancia Moodle, usuario y curso
- Establece cookie de sesión
- Redirige según rol y existencia de actividad

---

### GET `/api/lti-data`
**Descripción**: Obtiene datos de la sesión LTI actual.

**Autenticación**: Cookie LTI
**Respuesta**: JSON

```json
{
  "success": true,
  "session_id": "abc123...",
  "data": {
    "user_id": "123",
    "roles": "Instructor",
    "context_id": "course_123",
    "resource_link_id": "activity_456",
    ...
  }
}
```

---

## Administración

**Prefijo**: `/api/admin`

### POST `/api/admin/login`
**Descripción**: Inicia sesión de administrador y crea la cookie `admin_session` (24h).

**Autenticación**: No requerida
**Body**: JSON

```json
{
  "username": "admin",
  "password": "******"
}
```

**Respuesta**:
```json
{
  "success": true,
  "message": "Inicio de sesión exitoso"
}
```

---

### POST `/api/admin/logout`
**Descripción**: Cierra la sesión de administrador y elimina la cookie.

**Autenticación**: Cookie admin_session

---

### GET `/api/admin/check-session`
**Descripción**: Verifica si la sesión admin es válida y devuelve el usuario autenticado.

**Autenticación**: Cookie admin_session

**Respuesta**:
```json
{
  "success": true,
  "username": "admin"
}
```

---

### GET `/api/admin/statistics`
**Descripción**: Devuelve métricas globales (Moodle, cursos, actividades, usuarios, entregas, archivos, calificaciones).

**Autenticación**: Cookie admin_session

**Respuesta**:
```json
{
  "success": true,
  "data": {
    "moodle_instances": 1,
    "courses": 3,
    "activities": 8,
    "users": 120,
    "submissions": 45,
    "files": 45,
    "grades": 40
  }
}
```

---

### GET `/api/admin/moodle-instances`
**Descripción**: Lista todas las instancias Moodle registradas.

**Autenticación**: Cookie admin_session
**Respuesta**: JSON con `data` (array) y `count`.

---

### GET `/api/admin/courses`
**Descripción**: Lista todos los cursos.

**Autenticación**: Cookie admin_session
**Respuesta**: JSON con `data` (array) y `count`.

---

### GET `/api/admin/activities`
**Descripción**: Lista todas las actividades.

**Autenticación**: Cookie admin_session
**Respuesta**: JSON con `data` (array) y `count`.

---

### GET `/api/admin/users`
**Descripción**: Lista todos los usuarios.

**Autenticación**: Cookie admin_session
**Respuesta**: JSON con `data` (array) y `count`.

---

### GET `/api/admin/submissions`
**Descripción**: Lista todas las entregas de estudiantes.

**Autenticación**: Cookie admin_session
**Respuesta**: JSON con `data` (array) y `count`.

---

### GET `/api/admin/files`
**Descripción**: Lista todos los ficheros entregados.

**Autenticación**: Cookie admin_session
**Respuesta**: JSON con `data` (array) y `count`.

---

### GET `/api/admin/grades`
**Descripción**: Lista todas las calificaciones.

**Autenticación**: Cookie admin_session
**Respuesta**: JSON con `data` (array) y `count`.

---

## Actividades

**Prefijo**: `/api/activities`

### POST `/api/activities`
**Descripción**: Crea una nueva actividad.

**Autenticación**: Cookie LTI
**Permisos**: Profesores/administradores
**Body**: JSON

```json
{
  "title": "Práctica 1",
  "description": "Descripción de la actividad",
  "activity_type": "individual", // "individual" | "group"
  "max_group_size": null, // Requerido si activity_type="group" (mín. 2)
  "deadline": "2024-12-31T23:59:59Z", // Opcional, formato ISO 8601 UTC
  "evaluator_id": "23" // Opcional, ID del modelo LAMB
}
```

**Respuesta**:
```json
{
  "success": true,
  "message": "Actividad creada exitosamente",
  "activity": { ... }
}
```

---

### GET `/api/activities/{activity_id}`
**Descripción**: Obtiene una actividad específica.

**Autenticación**: Cookie LTI
**Permisos**: Profesores/administradores
**Respuesta**: `Activity`

---

### PUT `/api/activities/{activity_id}`
**Descripción**: Actualiza una actividad.

**Autenticación**: Cookie LTI
**Permisos**: Profesores/administradores (solo creador)
**Body**: JSON

```json
{
  "description": "Nueva descripción", // Opcional
  "deadline": "2024-12-31T23:59:59Z", // Opcional, formato ISO 8601 UTC
  "evaluator_id": "23" // Opcional
}
```

---

### GET `/api/activities/{activity_id}/view`
**Descripción**: Vista de actividad para estudiantes (actividad + su entrega).

**Autenticación**: Cookie LTI
**Permisos**: Estudiantes
**Respuesta**: `StudentActivityView`

```json
{
  "activity": { ... },
  "student_submission": { ... }, // null si no ha entregado
  "can_submit": true
}
```

---

### GET `/api/activities/{activity_id}/submissions`
**Descripción**: Lista todas las entregas de una actividad.

**Autenticación**: Cookie LTI
**Permisos**: Profesores/administradores
**Respuesta**: Array de `OptimizedSubmissionView`

---

### POST `/api/activities/{activity_id}/submissions`
**Descripción**: Crea una nueva entrega para la actividad.

**Autenticación**: Cookie LTI
**Permisos**: Estudiantes
**Tipo**: Multipart Form Data

**Form Data**:
- `file`: Archivo (máx. 50MB)

**Respuesta**:
```json
{
  "success": true,
  "message": "Documento enviado exitosamente",
  "submission": {
    "file_submission": { ... },
    "student_submission": { ... },
    "is_group_leader": true,
    "group_code_uses": 1
  }
}
```

**Notas**:
- Para actividades individuales: se crea una entrega individual
- Para actividades grupales: se genera un código de grupo único que otros estudiantes pueden usar para unirse
- Si ya existe una entrega, se reemplaza el archivo (solo para líderes de grupo o entregas individuales)

---

### POST `/api/activities/{activity_id}/evaluate`
**Descripción**: Evalúa automáticamente todas las entregas sin calificación usando LAMB.

**Autenticación**: Cookie LTI
**Permisos**: Profesores/administradores
**Requisitos**: La actividad debe tener configurado un `evaluator_id` (ID del modelo LAMB)
**Body** (opcional): JSON

```json
{
  "file_submission_ids": ["sub_123", "sub_456"] // Opcional: IDs específicos de entregas a evaluar
}
```

**Respuesta**: JSON

```json
{
  "success": true,
  "message": "Evaluación automática completada exitosamente",
  "grades_created": 15
}
```

**Notas**:
- Si no se proporciona `file_submission_ids`, evalúa todas las entregas sin calificación
- Si se proporciona `file_submission_ids`, solo evalúa las entregas especificadas
- Solo evalúa entregas que aún no tienen calificación
- Extrae texto de los documentos (PDF, DOCX, TXT)
- Envía el texto al modelo LAMB especificado
- Parsea la respuesta y crea calificaciones automáticamente

---

### POST `/api/activities/{activity_id}/grades/sync`
**Descripción**: Sincroniza todas las calificaciones con Moodle mediante LTI Outcome Service.

**Autenticación**: Cookie LTI
**Permisos**: Profesores/administradores
**Requisitos**: 
- Las entregas deben tener `lis_result_sourcedid` (proporcionado por Moodle en el lanzamiento LTI)
- Las entregas deben tener una calificación asignada
**Respuesta**: JSON

```json
{
  "success": true,
  "message": "Calificaciones enviadas: 15/15",
  "details": {
    "sent_count": 15,
    "failed_count": 0,
    "total_submissions": 15,
    "activity_title": "Práctica 1",
    "course_title": "Programación I",
    "results": [
      {
        "student_name": "Juan Pérez",
        "score": 8.5,
        "success": true
      }
    ]
  }
}
```

**Notas**:
- Las calificaciones se normalizan automáticamente de 0-10 a 0-1 para Moodle
- Solo se envían calificaciones que no han sido enviadas previamente
- Se marca cada entrega como `sent_to_moodle: true` después del envío exitoso

---

## Entregas (Submissions)

**Prefijo**: `/api/submissions`

### GET `/api/submissions/me`
**Descripción**: Obtiene la entrega actual del estudiante para la actividad del contexto LTI.

**Autenticación**: Cookie LTI
**Permisos**: Estudiantes
**Respuesta**: `OptimizedSubmissionView` o `null`

---

### POST `/api/submissions/join`
**Descripción**: Unirse a un grupo usando un código compartido.

**Autenticación**: Cookie LTI
**Permisos**: Estudiantes
**Body**: JSON

```json
{
  "activity_id": "123",
  "group_code": "ABC123"
}
```

**Respuesta**:
```json
{
  "success": true,
  "message": "Te has unido al grupo exitosamente",
  "submission": { ... }
}
```

---

### GET `/api/submissions/{submission_id}/members`
**Descripción**: Obtiene los miembros de una entrega grupal.

**Autenticación**: Cookie LTI
**Permisos**: Estudiantes
**Respuesta**: Array de miembros (ordenados por fecha de unión, el primero es el líder)

```json
[
  {
    "student_id": "123",
    "student_name": "Juan Pérez",
    "email": "juan@example.com",
    "is_group_leader": true,
    "submitted_at": "2024-01-15T10:30:00Z"
  },
  {
    "student_id": "456",
    "student_name": "María García",
    "email": "maria@example.com",
    "is_group_leader": false,
    "submitted_at": "2024-01-15T10:45:00Z"
  }
]
```

---

### GET `/api/downloads/{file_path:path}`
**Descripción**: Descarga archivos subidos por su ruta.

**Autenticación**: Cookie LTI
**Permisos**: Profesores/administradores
**Parámetros**:
- `file_path`: Ruta del archivo (URL encoded)

**Respuesta**: Archivo binario

**Notas**:
- El nombre del archivo descargado se personaliza automáticamente:
  - Para entregas grupales: usa el `group_code` como nombre
  - Para entregas individuales: usa el nombre del estudiante
- Solo permite acceso a archivos dentro del directorio `uploads/`

---

## Calificaciones (Grades)

**Prefijo**: `/api/grades`

### POST `/api/grades/{submission_id}`
**Descripción**: Crea o actualiza la calificación de una entrega específica.

**Autenticación**: Cookie LTI
**Permisos**: Profesores/administradores
**Body**: JSON

```json
{
  "score": 8.5, // Requerido: 0-10
  "comment": "Buen trabajo, código limpio y bien documentado" // Opcional
}
```

**Respuesta**:
```json
{
  "success": true,
  "message": "Calificación guardada exitosamente",
  "grade": {
    "id": "grade_123",
    "file_submission_id": "sub_123",
    "score": 8.5,
    "comment": "Buen trabajo...",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

**Notas**:
- Si ya existe una calificación para la entrega, se actualiza
- Si no existe, se crea una nueva
- El `submission_id` en la URL debe corresponder a un `file_submission_id` válido

---

## Archivos Estáticos

### GET `/favicon.png`
Sirve el favicon de la aplicación.

### GET `/config.js`
Sirve el archivo de configuración para la app SvelteKit.

### GET `/app/*`
Sirve los assets estáticos de SvelteKit (JS, CSS).

### GET `/img/*`
Sirve las imágenes de la aplicación.

### GET `/{path}`
Manejador SPA - sirve `index.html` para rutas no API.

---

## Códigos de Estado HTTP

| Código | Significado |
|--------|-------------|
| 200 | OK - Solicitud exitosa |
| 303 | See Other - Redirección LTI |
| 400 | Bad Request - Datos inválidos |
| 401 | Unauthorized - Sin sesión LTI/Admin |
| 403 | Forbidden - Sin permisos |
| 404 | Not Found - Recurso no encontrado |
| 500 | Internal Server Error - Error del servidor |

---

## Modelos de Datos

### Activity
```typescript
{
  id: string;
  title: string;
  description: string;
  activity_type: "individual" | "group";
  max_group_size?: number;
  creator_id: string;
  creator_moodle_id: string;
  created_at: string; // ISO 8601 UTC (ej: "2024-01-15T10:30:00Z")
  course_id: string;
  course_moodle_id: string;
  deadline?: string; // ISO 8601 UTC (ej: "2024-12-31T23:59:59Z")
  evaluator_id?: string;
}
```

### OptimizedSubmissionView
```typescript
{
  file_submission: {
    id: string;
    activity_id: string;
    file_name: string;
    file_path: string;
    file_size: number;
    file_type: string;
    uploaded_at: string; // ISO 8601 UTC
    uploaded_by: string;
    group_code?: string;
    max_group_members: number;
  };
  student_submission: {
    id: string;
    file_submission_id: string;
    student_id: string;
    activity_id: string;
    lis_result_sourcedid?: string;
    joined_at: string; // ISO 8601 UTC
    sent_to_moodle: boolean;
    sent_to_moodle_at?: string; // ISO 8601 UTC
  };
  student_name?: string;
  student_email?: string;
  is_group_leader: boolean;
  group_code_uses?: number;
  grade?: Grade;
}
```

### Grade
```typescript
{
  id: string;
  file_submission_id: string;
  score: number; // 0-10
  comment?: string;
  created_at: string; // ISO 8601 UTC (ej: "2024-01-15T10:30:00Z")
}
```

### GradeUpdate (usado en POST /api/grades/{submission_id})
```typescript
{
  score: number; // Requerido: 0-10
  comment?: string; // Opcional
}
```
**Nota**: El `file_submission_id` se toma del path parameter, no del body.

---

## Resumen de Endpoints

### Total: 26 endpoints

#### LTI (2)
- `POST /lti`
- `GET /api/lti-data`

#### Administración (11)
- `POST /api/admin/login`
- `POST /api/admin/logout`
- `GET /api/admin/check-session`
- `GET /api/admin/statistics`
- `GET /api/admin/moodle-instances`
- `GET /api/admin/courses`
- `GET /api/admin/activities`
- `GET /api/admin/users`
- `GET /api/admin/submissions`
- `GET /api/admin/files`
- `GET /api/admin/grades`

#### Actividades (8)
- `POST /api/activities`
- `GET /api/activities/{id}`
- `PUT /api/activities/{id}`
- `GET /api/activities/{id}/view`
- `GET /api/activities/{id}/submissions`
- `POST /api/activities/{id}/submissions`
- `POST /api/activities/{id}/evaluate`
- `POST /api/activities/{id}/grades/sync`

#### Entregas (4)
- `GET /api/submissions/me`
- `POST /api/submissions/join`
- `GET /api/submissions/{id}/members`
- `GET /api/downloads/{file_path:path}`

#### Calificaciones (1)
- `POST /api/grades/{submission_id}`

---

## Ejemplos de Uso

### Crear una actividad
```bash
curl -X POST http://localhost:9099/api/activities \
  -H "Content-Type: application/json" \
  -b "lti_session=abc123..." \
  -d '{
    "title": "Práctica 1",
    "description": "Implementar un algoritmo de ordenación",
    "activity_type": "individual",
    "deadline": "2024-12-31T23:59:59Z",
    "evaluator_id": "23"
  }'
```

### Subir una entrega
```bash
curl -X POST http://localhost:9099/api/activities/13946/submissions \
  -b "lti_session=abc123..." \
  -F "file=@documento.pdf"
```

### Calificar una entrega
```bash
curl -X POST http://localhost:9099/api/grades/sub_123 \
  -H "Content-Type: application/json" \
  -b "lti_session=abc123..." \
  -d '{
    "score": 8.5,
    "comment": "Buen trabajo, código limpio y bien documentado"
  }'
```

### Sincronizar calificaciones con Moodle
```bash
curl -X POST http://localhost:9099/api/activities/13946/grades/sync \
  -b "lti_session=abc123..."
```

### Unirse a un grupo
```bash
curl -X POST http://localhost:9099/api/submissions/join \
  -H "Content-Type: application/json" \
  -b "lti_session=abc123..." \
  -d '{
    "activity_id": "13946",
    "group_code": "ABC123"
  }'
```

---

## Flujos de Trabajo

### Flujo de Actividad Individual

1. **Profesor crea actividad** → `POST /api/activities`
2. **Estudiante ve actividad** → `GET /api/activities/{id}/view`
3. **Estudiante sube documento** → `POST /api/activities/{id}/submissions`
4. **Profesor ve entregas** → `GET /api/activities/{id}/submissions`
5. **Profesor evalúa** (automática o manual):
   - Evaluación automática → `POST /api/activities/{id}/evaluate`
   - Calificación manual → `POST /api/grades/{submission_id}`
6. **Profesor sincroniza con Moodle** → `POST /api/activities/{id}/grades/sync`

### Flujo de Actividad Grupal

1. **Profesor crea actividad grupal** → `POST /api/activities` (con `activity_type: "group"` y `max_group_size`)
2. **Primer estudiante (líder) sube documento** → `POST /api/activities/{id}/submissions`
   - Se genera un código de grupo único (ej: "ABC123")
3. **Líder comparte código** con compañeros de grupo
4. **Otros estudiantes se unen al grupo** → `POST /api/submissions/join` (con el código)
5. **Estudiantes ven miembros del grupo** → `GET /api/submissions/{submission_id}/members`
6. **Profesor ve entregas agrupadas** → `GET /api/activities/{id}/submissions`
7. **Profesor califica la entrega grupal** → `POST /api/grades/{submission_id}`
   - La calificación se aplica a todos los miembros del grupo
8. **Profesor sincroniza con Moodle** → `POST /api/activities/{id}/grades/sync`
   - Cada estudiante recibe la misma calificación en Moodle

### Flujo de Evaluación Automática con LAMB

1. **Profesor configura evaluador** → `PUT /api/activities/{id}` (con `evaluator_id`)
2. **Estudiantes suben documentos** → `POST /api/activities/{id}/submissions`
3. **Profesor inicia evaluación automática** → `POST /api/activities/{id}/evaluate`
   - El sistema extrae texto de cada documento (PDF, DOCX, TXT)
   - Envía el texto al modelo LAMB especificado
   - Parsea la respuesta y crea calificaciones automáticamente
4. **Profesor revisa y ajusta calificaciones** (opcional) → `POST /api/grades/{submission_id}`
5. **Profesor sincroniza con Moodle** → `POST /api/activities/{id}/grades/sync`

---

## Documentación Interactiva

FastAPI genera documentación interactiva automáticamente:

- **Swagger UI**: http://localhost:9099/docs
- **ReDoc**: http://localhost:9099/redoc

---

## Mejoras RESTful Implementadas

✅ **Estructura de recursos clara**: Actividades, Entregas y Calificaciones como recursos independientes

✅ **Verbos HTTP semánticos**: 
- POST para crear
- GET para leer
- PUT para actualizar

✅ **URIs descriptivas**: 
- `/api/activities` en lugar de `/api/activities/create`
- `/api/grades/{id}` en lugar de `/api/activities/grade/individual`

✅ **Jerarquía lógica**: 
- `/api/activities/{id}/submissions` para entregas de una actividad
- `/api/submissions/{id}/members` para miembros de una entrega

✅ **Acciones especiales claras**:
- `/api/activities/{id}/evaluate` para evaluación automática
- `/api/activities/{id}/grades/sync` para sincronización

✅ **Consistencia**: Todos los endpoints siguen las mismas convenciones

---

## Notas Importantes

1. **Sesión LTI**: Requerida para todos los endpoints (excepto `/lti`)

2. **Permisos**: Basados en roles del lanzamiento LTI

3. **Archivos**: Almacenados en `backend/uploads/{moodle}/{course}/{activity}/`

4. **Límite de tamaño**: 50MB por archivo

5. **Calificaciones**: Normalizadas automáticamente de 0-10 a 0-1 para Moodle

6. **Evaluación automática**: Requiere `evaluator_id` configurado en la actividad

7. **Formato de fechas**: Todas las fechas usan formato ISO 8601 con zona horaria UTC (ej: `2024-12-31T23:59:59Z`)
   - El sufijo `Z` indica UTC (Coordinated Universal Time)
   - El frontend convierte automáticamente a la hora local del navegador
   - Al enviar fechas al backend, usar `.toISOString()` en JavaScript

8. **Sesión admin**: Las credenciales provienen de `ADMIN_USERNAME` y `ADMIN_PASSWORD`. La cookie `admin_session` dura 24h (httpOnly, `secure` si HTTPS).
