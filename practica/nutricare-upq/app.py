"""
========================================================================================
SISTEMA WEB: NUTRICARE UPQ - CLÍNICA DE NUTRICIÓN INTEGRAL
========================================================================================
Materia: Aplicaciones Web
Carrera: Ingeniería en Tecnologías de la Información e Innovación Digital
Institución: Universidad Politécnica de Querétaro (UPQ)

DESCRIPCIÓN GENERAL:
Este microframework desarrollado en Flask implementa el ciclo completo de atención
en el área de la salud (Nutrición), dando cumplimiento a los requerimientos:
- Etapa 2: Gestión de 3 roles principales (Administrador, Médico/Nutriólogo y Paciente).
- Etapa 3: Cumplimiento de requerimientos funcionales (RF01 a RF12) y no funcionales
  (RNF01 a RNF06), incluyendo reglas de negocio de no-empalme de citas, integridad
  referencial y privacidad médica.
- Etapa 7: Desarrollo de interfaces con Flask, Jinja2 y DaisyUI (Tailwind CSS).
========================================================================================
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from functools import wraps
from datetime import datetime

# Inicialización de la aplicación Flask
app = Flask(__name__)
# Llave secreta para la firma de sesiones y mensajes flash
app.secret_key = 'nutricare_secret_key_upq_2026'

# Ruta absoluta al archivo de base de datos relacional SQLite
DB_PATH = os.path.join(os.path.dirname(__file__), "nutricare.db")

def get_db():
    """
    Establece la conexión con la base de datos SQLite.
    Habilita el modo de diccionario por filas (Row) y asegura la integridad referencial
    mediante el encendido de claves foráneas (PRAGMA foreign_keys = ON).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def login_required(roles=None):
    """
    Decorador de control de acceso basado en roles (RBAC).
    
    Parámetros:
        roles (list, opcional): Lista de nombres de roles con permiso (ej. ['Administrador', 'Médico']).
        
    Comportamiento:
        - Si el usuario no ha iniciado sesión, redirige al login con alerta 'warning'.
        - Si el usuario no posee el rol autorizado, bloquea el acceso y redirige a su dashboard respectivo.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Por favor inicia sesión para acceder al sistema.', 'warning')
                return redirect(url_for('login'))
            if roles and session.get('role_name') not in roles:
                flash('No tienes permisos para acceder a este módulo.', 'error')
                return redirect(url_for('dashboard_redirect'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ========================================================================================
# RUTAS DE ENRUTAMIENTO GENERAL Y CONTROL DE FLUJO
# ========================================================================================

@app.route('/')
def index():
    """Ruta raíz: Redirige automáticamente al dashboard si hay sesión activa, o al login."""
    if 'user_id' in session:
        return redirect(url_for('dashboard_redirect'))
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard_redirect():
    """Redirecciona al dashboard correspondiente de acuerdo con el rol autenticado."""
    role = session.get('role_name')
    if role == 'Administrador':
        return redirect(url_for('admin_dashboard'))
    elif role == 'Médico':
        return redirect(url_for('medico_dashboard'))
    elif role == 'Paciente':
        return redirect(url_for('paciente_dashboard'))
    return redirect(url_for('login'))

# ========================================================================================
# ETAPA 3: REQUERIMIENTO RF01 - INICIO DE SESIÓN Y AUTENTICACIÓN
# ========================================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    RF01: Control de acceso para Administrador, Médico y Paciente.
    Valida credenciales, comprueba si la cuenta está activa y guarda variables de sesión:
    user_id, user_name, role_name, nutriologo_id / paciente_id según corresponda.
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            SELECT u.id_usuario, u.id_rol, u.nombre, u.apellido, u.email, u.password, u.activo, r.nombre_rol
            FROM usuarios u
            JOIN roles r ON u.id_rol = r.id_rol
            WHERE u.email = ?
        """, (email,))
        user = cursor.fetchone()

        if user and user['password'] == password:
            # Validación de cuenta habilitada
            if not user['activo']:
                flash('Esta cuenta se encuentra temporalmente desactivada. Contacta al administrador.', 'error')
                return redirect(url_for('login'))

            # Carga de contexto en sesión
            session['user_id'] = user['id_usuario']
            session['user_name'] = f"{user['nombre']} {user['apellido']}"
            session['role_id'] = user['id_rol']
            session['role_name'] = user['nombre_rol']
            session['email'] = user['email']

            # Identificación de identificadores clínicos asociados
            if user['nombre_rol'] == 'Médico':
                cursor.execute("SELECT id_nutriologo FROM nutriologos WHERE id_usuario = ?", (user['id_usuario'],))
                nutri = cursor.fetchone()
                session['nutriologo_id'] = nutri['id_nutriologo'] if nutri else None
            elif user['nombre_rol'] == 'Paciente':
                cursor.execute("SELECT id_paciente FROM pacientes WHERE id_usuario = ?", (user['id_usuario'],))
                pac = cursor.fetchone()
                session['paciente_id'] = pac['id_paciente'] if pac else None

            flash(f'¡Bienvenido(a), {session["user_name"]}!', 'success')
            return redirect(url_for('dashboard_redirect'))
        else:
            flash('Correo electrónico o contraseña incorrectos.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Finaliza la sesión del usuario eliminando todos los datos en memoria."""
    session.clear()
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('login'))

# ========================================================================================
# ETAPA 2 & 3: MÓDULO ADMINISTRADOR
# Funcionalidades: Gestionar usuarios, consultar pacientes, dar de alta y desactivar médicos.
# ========================================================================================

@app.route('/admin/dashboard')
@login_required(roles=['Administrador'])
def admin_dashboard():
    """
    RF12: Dashboard Administrativo.
    Muestra estadísticas globales: total de pacientes, total de nutriólogos, total de citas
    y tabla de actividad reciente en tiempo real.
    """
    db = get_db()
    cursor = db.cursor()

    total_pacientes = cursor.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0]
    total_nutriologos = cursor.execute("SELECT COUNT(*) FROM nutriologos").fetchone()[0]
    total_citas = cursor.execute("SELECT COUNT(*) FROM citas").fetchone()[0]
    citas_hoy = cursor.execute("SELECT COUNT(*) FROM citas WHERE fecha_cita = date('now')").fetchone()[0]

    # Consulta de citas recientes con nombres de pacientes y nutriólogos
    citas_recientes = cursor.execute("""
        SELECT c.id_cita, c.fecha_cita, c.hora_cita, c.motivo, c.estado,
               (u_p.nombre || ' ' || u_p.apellido) AS paciente,
               (u_m.nombre || ' ' || u_m.apellido) AS nutriologo
        FROM citas c
        JOIN pacientes p ON c.id_paciente = p.id_paciente
        JOIN usuarios u_p ON p.id_usuario = u_p.id_usuario
        JOIN nutriologos n ON c.id_nutriologo = n.id_nutriologo
        JOIN usuarios u_m ON n.id_usuario = u_m.id_usuario
        ORDER BY c.fecha_cita DESC, c.hora_cita DESC LIMIT 5
    """).fetchall()

    return render_template('admin/dashboard.html',
                           total_pacientes=total_pacientes,
                           total_nutriologos=total_nutriologos,
                           total_citas=total_citas,
                           citas_hoy=citas_hoy,
                           citas_recientes=citas_recientes)

@app.route('/admin/nutriologos')
@login_required(roles=['Administrador'])
def admin_nutriologos():
    """RF02: Lista completa de médicos/nutriólogos registrados en la clínica."""
    db = get_db()
    cursor = db.cursor()
    nutriologos = cursor.execute("""
        SELECT n.id_nutriologo, n.cedula_profesional, n.especialidad, n.horario_inicio, n.horario_fin,
               u.id_usuario, u.nombre, u.apellido, u.email, u.telefono, u.activo
        FROM nutriologos n
        JOIN usuarios u ON n.id_usuario = u.id_usuario
        ORDER BY u.nombre ASC
    """).fetchall()
    return render_template('admin/nutriologos.html', nutriologos=nutriologos)

@app.route('/admin/nutriologos/nuevo', methods=['POST'])
@login_required(roles=['Administrador'])
def admin_crear_nutriologo():
    """
    RF02: Registrar nuevo especialista médico en el sistema.
    Crea el registro en la tabla usuarios (id_rol=2) y la extensión en nutriologos.
    """
    nombre = request.form.get('nombre')
    apellido = request.form.get('apellido')
    email = request.form.get('email')
    password = request.form.get('password')
    telefono = request.form.get('telefono')
    cedula = request.form.get('cedula')
    especialidad = request.form.get('especialidad')
    horario_inicio = request.form.get('horario_inicio', '08:00')
    horario_fin = request.form.get('horario_fin', '18:00')

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("""
            INSERT INTO usuarios (id_rol, nombre, apellido, email, password, telefono, activo)
            VALUES (2, ?, ?, ?, ?, ?, 1)
        """, (nombre, apellido, email, password, telefono))
        id_usuario = cursor.lastrowid

        cursor.execute("""
            INSERT INTO nutriologos (id_usuario, cedula_profesional, especialidad, horario_inicio, horario_fin)
            VALUES (?, ?, ?, ?, ?)
        """, (id_usuario, cedula, especialidad, horario_inicio, horario_fin))

        db.commit()
        flash(f'Nutriólogo(a) {nombre} {apellido} registrado exitosamente.', 'success')
    except sqlite3.IntegrityError:
        flash('El correo ingresado ya se encuentra registrado.', 'error')

    return redirect(url_for('admin_nutriologos'))

@app.route('/admin/nutriologos/toggle/<int:id_usuario>')
@login_required(roles=['Administrador'])
def admin_toggle_nutriologo(id_usuario):
    """RF02: Desactivar o reactivar la cuenta de un nutriólogo para revocar su acceso."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE usuarios SET activo = CASE WHEN activo = 1 THEN 0 ELSE 1 END WHERE id_usuario = ?", (id_usuario,))
    db.commit()
    flash('Estado del especialista actualizado correctamente.', 'info')
    return redirect(url_for('admin_nutriologos'))

@app.route('/admin/pacientes')
@login_required(roles=['Administrador'])
def admin_pacientes():
    """Consulta general de expedientes de pacientes dados de alta en la clínica."""
    db = get_db()
    cursor = db.cursor()
    pacientes = cursor.execute("""
        SELECT p.id_paciente, p.sexo, p.estatura_cm, p.alergias, p.objetivo_salud,
               u.nombre, u.apellido, u.email, u.telefono, u.fecha_registro
        FROM pacientes p
        JOIN usuarios u ON p.id_usuario = u.id_usuario
        ORDER BY u.nombre ASC
    """).fetchall()
    return render_template('admin/pacientes.html', pacientes=pacientes)

# ========================================================================================
# ETAPA 2 & 3: MÓDULO MÉDICO / NUTRIÓLOGO
# Funcionalidades: Gestionar citas, registrar consultas antropométricas, prescribir menús.
# ========================================================================================

@app.route('/medico/dashboard')
@login_required(roles=['Médico'])
def medico_dashboard():
    """
    Dashboard del Nutriólogo:
    Muestra citas del día actual, próximas consultas agendadas y conteo de pacientes a su cargo.
    """
    nutriologo_id = session.get('nutriologo_id')
    db = get_db()
    cursor = db.cursor()

    citas_hoy = cursor.execute("""
        SELECT c.id_cita, c.hora_cita, c.motivo, c.estado,
               (u.nombre || ' ' || u.apellido) AS paciente, p.id_paciente, u.telefono
        FROM citas c
        JOIN pacientes p ON c.id_paciente = p.id_paciente
        JOIN usuarios u ON p.id_usuario = u.id_usuario
        WHERE c.id_nutriologo = ? AND c.fecha_cita = date('now')
        ORDER BY c.hora_cita ASC
    """, (nutriologo_id,)).fetchall()

    proximas_citas = cursor.execute("""
        SELECT c.id_cita, c.fecha_cita, c.hora_cita, c.motivo, c.estado,
               (u.nombre || ' ' || u.apellido) AS paciente, p.id_paciente
        FROM citas c
        JOIN pacientes p ON c.id_paciente = p.id_paciente
        JOIN usuarios u ON p.id_usuario = u.id_usuario
        WHERE c.id_nutriologo = ? AND c.fecha_cita >= date('now')
        ORDER BY c.fecha_cita ASC, c.hora_cita ASC LIMIT 6
    """, (nutriologo_id,)).fetchall()

    total_pacientes = cursor.execute("""
        SELECT COUNT(DISTINCT id_paciente) FROM citas WHERE id_nutriologo = ?
    """, (nutriologo_id,)).fetchone()[0]

    total_consultas_mes = cursor.execute("""
        SELECT COUNT(*) FROM consultas_antropometricas WHERE id_nutriologo = ?
    """, (nutriologo_id,)).fetchone()[0]

    return render_template('medico/dashboard.html',
                           citas_hoy=citas_hoy,
                           proximas_citas=proximas_citas,
                           total_pacientes=total_pacientes,
                           total_consultas_mes=total_consultas_mes)

@app.route('/medico/citas')
@login_required(roles=['Médico'])
def medico_citas():
    """RF06: Agenda médica con filtro exclusivo para las consultas del nutriólogo autenticado."""
    nutriologo_id = session.get('nutriologo_id')
    db = get_db()
    cursor = db.cursor()
    citas = cursor.execute("""
        SELECT c.id_cita, c.fecha_cita, c.hora_cita, c.motivo, c.estado,
               (u.nombre || ' ' || u.apellido) AS paciente, p.id_paciente, u.telefono, u.email
        FROM citas c
        JOIN pacientes p ON c.id_paciente = p.id_paciente
        JOIN usuarios u ON p.id_usuario = u.id_usuario
        WHERE c.id_nutriologo = ?
        ORDER BY c.fecha_cita DESC, c.hora_cita DESC
    """, (nutriologo_id,)).fetchall()
    return render_template('medico/citas.html', citas=citas)

@app.route('/medico/citas/estado/<int:id_cita>/<string:nuevo_estado>')
@login_required(roles=['Médico'])
def medico_cambiar_estado_cita(id_cita, nuevo_estado):
    """
    RF06: Actualización de estado de la cita ('Confirmada', 'Completada', 'Cancelada').
    Garantiza que el registro nunca se elimine de la base de datos (Regla de negocio).
    """
    if nuevo_estado in ['Confirmada', 'Completada', 'Cancelada']:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE citas SET estado = ? WHERE id_cita = ? AND id_nutriologo = ?", 
                       (nuevo_estado, id_cita, session.get('nutriologo_id')))
        db.commit()
        flash(f'Cita actualizada a "{nuevo_estado}".', 'success')
    return redirect(url_for('medico_citas'))

@app.route('/medico/pacientes')
@login_required(roles=['Médico'])
def medico_pacientes():
    """Directorio de pacientes asignados con acceso directo a consultas y menús."""
    nutriologo_id = session.get('nutriologo_id')
    db = get_db()
    cursor = db.cursor()
    pacientes = cursor.execute("""
        SELECT p.id_paciente, p.sexo, p.estatura_cm, p.alergias, p.objetivo_salud,
               u.nombre, u.apellido, u.email, u.telefono,
               (SELECT peso_kg FROM consultas_antropometricas WHERE id_paciente = p.id_paciente ORDER BY fecha_evaluacion DESC LIMIT 1) as ultimo_peso,
               (SELECT imc FROM consultas_antropometricas WHERE id_paciente = p.id_paciente ORDER BY fecha_evaluacion DESC LIMIT 1) as ultimo_imc
        FROM pacientes p
        JOIN usuarios u ON p.id_usuario = u.id_usuario
        ORDER BY u.nombre ASC
    """).fetchall()
    return render_template('medico/pacientes.html', pacientes=pacientes)

@app.route('/medico/consulta/<int:id_paciente>', methods=['GET', 'POST'])
@login_required(roles=['Médico'])
def medico_consulta(id_paciente):
    """
    RF07: Registro de consulta nutricional y antropometría completa.
    Calcula el Índice de Masa Corporal (IMC = peso / estatura_m^2),
    guarda masa muscular, grasa %, circunferencias y diagnóstico médico.
    """
    nutriologo_id = session.get('nutriologo_id')
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        peso = float(request.form.get('peso_kg'))
        estatura_cm = float(request.form.get('estatura_cm', 165.0))
        estatura_m = estatura_cm / 100.0
        imc = round(peso / (estatura_m ** 2), 2)
        grasa = float(request.form.get('porcentaje_grasa', 0))
        musculo = float(request.form.get('masa_muscular_kg', 0))
        cintura = float(request.form.get('circunferencia_cintura', 0))
        cadera = float(request.form.get('circunferencia_cadera', 0))
        notas = request.form.get('diagnostico_notas', '')
        fecha = request.form.get('fecha_evaluacion', datetime.now().strftime('%Y-%m-%d'))

        # Actualización de talla base del paciente
        cursor.execute("UPDATE pacientes SET estatura_cm = ? WHERE id_paciente = ?", (estatura_cm, id_paciente))

        # Inserción en historial antropométrico
        cursor.execute("""
            INSERT INTO consultas_antropometricas 
            (id_paciente, id_nutriologo, fecha_evaluacion, peso_kg, imc, porcentaje_grasa, masa_muscular_kg, circunferencia_cintura, circunferencia_cadera, diagnostico_notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (id_paciente, nutriologo_id, fecha, peso, imc, grasa, musculo, cintura, cadera, notas))
        db.commit()

        flash('Consulta y medidas antropométricas registradas con éxito.', 'success')
        return redirect(url_for('medico_historial_paciente', id_paciente=id_paciente))

    cursor.execute("""
        SELECT p.*, (u.nombre || ' ' || u.apellido) AS nombre_completo, u.email, u.telefono
        FROM pacientes p JOIN usuarios u ON p.id_usuario = u.id_usuario
        WHERE p.id_paciente = ?
    """, (id_paciente,))
    paciente = cursor.fetchone()

    return render_template('medico/consulta.html', paciente=paciente)

@app.route('/medico/historial/<int:id_paciente>')
@login_required(roles=['Médico'])
def medico_historial_paciente(id_paciente):
    """RF10: Consulta del expediente histórico de consultas y planes del paciente."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT p.*, (u.nombre || ' ' || u.apellido) AS nombre_completo, u.email, u.telefono
        FROM pacientes p JOIN usuarios u ON p.id_usuario = u.id_usuario
        WHERE p.id_paciente = ?
    """, (id_paciente,))
    paciente = cursor.fetchone()

    consultas = cursor.execute("""
        SELECT ca.*, (u.nombre || ' ' || u.apellido) AS nutriologo
        FROM consultas_antropometricas ca
        JOIN nutriologos n ON ca.id_nutriologo = n.id_nutriologo
        JOIN usuarios u ON n.id_usuario = u.id_usuario
        WHERE ca.id_paciente = ?
        ORDER BY ca.fecha_evaluacion DESC
    """, (id_paciente,)).fetchall()

    planes = cursor.execute("""
        SELECT pa.*, (u.nombre || ' ' || u.apellido) AS nutriologo
        FROM planes_alimenticios pa
        JOIN nutriologos n ON pa.id_nutriologo = n.id_nutriologo
        JOIN usuarios u ON n.id_usuario = u.id_usuario
        WHERE pa.id_paciente = ?
        ORDER BY pa.fecha_inicio DESC
    """, (id_paciente,)).fetchall()

    return render_template('medico/historial.html', paciente=paciente, consultas=consultas, planes=planes)

@app.route('/medico/plan/<int:id_paciente>', methods=['GET', 'POST'])
@login_required(roles=['Médico'])
def medico_crear_plan(id_paciente):
    """
    RF08: Prescripción de plan de alimentación y dietocálculo.
    Desactiva planes previos del paciente e inserta la distribución de comidas:
    Desayuno, Colación 1, Comida, Colación 2 y Cena con sus recomendaciones.
    """
    nutriologo_id = session.get('nutriologo_id')
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        titulo = request.form.get('titulo_plan')
        calorias = int(request.form.get('calorias_totales', 2000))
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')

        cursor.execute("UPDATE planes_alimenticios SET activo = 0 WHERE id_paciente = ?", (id_paciente,))

        cursor.execute("""
            INSERT INTO planes_alimenticios (id_paciente, id_nutriologo, titulo_plan, calorias_totales, fecha_inicio, fecha_fin, activo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (id_paciente, nutriologo_id, titulo, calorias, fecha_inicio, fecha_fin))
        id_plan = cursor.lastrowid

        momentos = ['Desayuno', 'Colación Matutina', 'Comida', 'Colación Vespertina', 'Cena']
        for momento in momentos:
            desc = request.form.get(f'desc_{momento}', '').strip()
            recom = request.form.get(f'recom_{momento}', '').strip()
            if desc:
                cursor.execute("""
                    INSERT INTO comidas_detalle (id_plan, momento, descripcion_alimentos, recomendaciones)
                    VALUES (?, ?, ?, ?)
                """, (id_plan, momento, desc, recom))

        db.commit()
        flash('Plan de alimentación prescrito y activado correctamente.', 'success')
        return redirect(url_for('medico_historial_paciente', id_paciente=id_paciente))

    cursor.execute("""
        SELECT p.*, (u.nombre || ' ' || u.apellido) AS nombre_completo
        FROM pacientes p JOIN usuarios u ON p.id_usuario = u.id_usuario
        WHERE p.id_paciente = ?
    """, (id_paciente,))
    paciente = cursor.fetchone()

    return render_template('medico/plan.html', paciente=paciente)

# ========================================================================================
# ETAPA 2 & 3: MÓDULO PACIENTE
# Funcionalidades: Solicitar citas sin empalmes, ver evolución, consultar menú activo.
# ========================================================================================

@app.route('/paciente/dashboard')
@login_required(roles=['Paciente'])
def paciente_dashboard():
    """
    Dashboard del Paciente:
    Muestra la próxima cita confirmada, última medición antropométrica e información del menú activo.
    """
    paciente_id = session.get('paciente_id')
    db = get_db()
    cursor = db.cursor()

    proxima_cita = cursor.execute("""
        SELECT c.*, (u.nombre || ' ' || u.apellido) AS nutriologo, n.especialidad
        FROM citas c
        JOIN nutriologos n ON c.id_nutriologo = n.id_nutriologo
        JOIN usuarios u ON n.id_usuario = u.id_usuario
        WHERE c.id_paciente = ? AND c.estado IN ('Pendiente', 'Confirmada') AND c.fecha_cita >= date('now')
        ORDER BY c.fecha_cita ASC, c.hora_cita ASC LIMIT 1
    """, (paciente_id,)).fetchone()

    ultima_medicion = cursor.execute("""
        SELECT * FROM consultas_antropometricas
        WHERE id_paciente = ?
        ORDER BY fecha_evaluacion DESC LIMIT 1
    """, (paciente_id,)).fetchone()

    plan_activo = cursor.execute("""
        SELECT pa.*, (u.nombre || ' ' || u.apellido) AS nutriologo
        FROM planes_alimenticios pa
        JOIN nutriologos n ON pa.id_nutriologo = n.id_nutriologo
        JOIN usuarios u ON n.id_usuario = u.id_usuario
        WHERE pa.id_paciente = ? AND pa.activo = 1
        ORDER BY pa.id_plan DESC LIMIT 1
    """, (paciente_id,)).fetchone()

    return render_template('paciente/dashboard.html',
                           proxima_cita=proxima_cita,
                           ultima_medicion=ultima_medicion,
                           plan_activo=plan_activo)

@app.route('/paciente/citas', methods=['GET', 'POST'])
@login_required(roles=['Paciente'])
def paciente_citas():
    """
    RF04 y RF05: Solicitud de citas y prevención de citas duplicadas.
    REGLA DE NEGOCIO: Un paciente no podrá solicitar una cita en un horario ocupado por el médico.
    """
    paciente_id = session.get('paciente_id')
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        id_nutriologo = request.form.get('id_nutriologo')
        fecha_cita = request.form.get('fecha_cita')
        hora_cita = request.form.get('hora_cita')
        motivo = request.form.get('motivo')

        # Verificación de colisión de horario en la base de datos
        ocupado = cursor.execute("""
            SELECT id_cita FROM citas 
            WHERE id_nutriologo = ? AND fecha_cita = ? AND hora_cita = ? AND estado != 'Cancelada'
        """, (id_nutriologo, fecha_cita, hora_cita)).fetchone()

        if ocupado:
            flash('Lo sentimos, este horario ya está ocupado con el especialista. Por favor selecciona otra hora u otro día.', 'error')
        else:
            cursor.execute("""
                INSERT INTO citas (id_paciente, id_nutriologo, fecha_cita, hora_cita, motivo, estado)
                VALUES (?, ?, ?, ?, ?, 'Pendiente')
            """, (paciente_id, id_nutriologo, fecha_cita, hora_cita, motivo))
            db.commit()
            flash('¡Cita solicitada con éxito! Espera la confirmación de tu nutriólogo.', 'success')
            return redirect(url_for('paciente_citas'))

    mis_citas = cursor.execute("""
        SELECT c.*, (u.nombre || ' ' || u.apellido) AS nutriologo, n.especialidad
        FROM citas c
        JOIN nutriologos n ON c.id_nutriologo = n.id_nutriologo
        JOIN usuarios u ON n.id_usuario = u.id_usuario
        WHERE c.id_paciente = ?
        ORDER BY c.fecha_cita DESC, c.hora_cita DESC
    """, (paciente_id,)).fetchall()

    nutriologos = cursor.execute("""
        SELECT n.id_nutriologo, (u.nombre || ' ' || u.apellido) AS nombre_completo, n.especialidad, n.horario_inicio, n.horario_fin
        FROM nutriologos n
        JOIN usuarios u ON n.id_usuario = u.id_usuario
        WHERE u.activo = 1
    """).fetchall()

    return render_template('paciente/citas.html', mis_citas=mis_citas, nutriologos=nutriologos)

@app.route('/paciente/citas/cancelar/<int:id_cita>')
@login_required(roles=['Paciente'])
def paciente_cancelar_cita(id_cita):
    """
    Cancelación de citas por parte del paciente.
    REGLA DE NEGOCIO: Las citas canceladas conservan su registro (eliminación lógica).
    """
    paciente_id = session.get('paciente_id')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE citas SET estado = 'Cancelada'
        WHERE id_cita = ? AND id_paciente = ? AND estado != 'Completada'
    """, (id_cita, paciente_id))
    db.commit()
    flash('Tu cita ha sido cancelada.', 'info')
    return redirect(url_for('paciente_citas'))

@app.route('/paciente/expediente')
@login_required(roles=['Paciente'])
def paciente_expediente():
    """
    RF10: Expediente y gráfica interactiva antropométrica.
    Envía los datos de peso, porcentaje de grasa y masa muscular serializados en JSON para Chart.js.
    """
    paciente_id = session.get('paciente_id')
    db = get_db()
    cursor = db.cursor()

    paciente = cursor.execute("""
        SELECT p.*, (u.nombre || ' ' || u.apellido) AS nombre_completo, u.email, u.telefono
        FROM pacientes p JOIN usuarios u ON p.id_usuario = u.id_usuario
        WHERE p.id_paciente = ?
    """, (paciente_id,)).fetchone()

    evaluaciones = cursor.execute("""
        SELECT ca.*, (u.nombre || ' ' || u.apellido) AS nutriologo
        FROM consultas_antropometricas ca
        JOIN nutriologos n ON ca.id_nutriologo = n.id_nutriologo
        JOIN usuarios u ON n.id_usuario = u.id_usuario
        WHERE ca.id_paciente = ?
        ORDER BY ca.fecha_evaluacion ASC
    """, (paciente_id,)).fetchall()

    fechas = [e['fecha_evaluacion'] for e in evaluaciones]
    pesos = [e['peso_kg'] for e in evaluaciones]
    grasas = [e['porcentaje_grasa'] for e in evaluaciones]
    musculos = [e['masa_muscular_kg'] for e in evaluaciones]

    return render_template('paciente/expediente.html',
                           paciente=paciente,
                           evaluaciones=evaluaciones,
                           fechas=fechas,
                           pesos=pesos,
                           grasas=grasas,
                           musculos=musculos)

@app.route('/paciente/plan')
@login_required(roles=['Paciente'])
def paciente_plan():
    """RF09: Consulta del plan de alimentación activo asignado al paciente."""
    paciente_id = session.get('paciente_id')
    db = get_db()
    cursor = db.cursor()

    plan = cursor.execute("""
        SELECT pa.*, (u.nombre || ' ' || u.apellido) AS nutriologo, n.especialidad
        FROM planes_alimenticios pa
        JOIN nutriologos n ON pa.id_nutriologo = n.id_nutriologo
        JOIN usuarios u ON n.id_usuario = u.id_usuario
        WHERE pa.id_paciente = ? AND pa.activo = 1
        ORDER BY pa.id_plan DESC LIMIT 1
    """, (paciente_id,)).fetchone()

    comidas = []
    if plan:
        comidas = cursor.execute("""
            SELECT * FROM comidas_detalle WHERE id_plan = ? ORDER BY id_comida ASC
        """, (plan['id_plan'],)).fetchall()

    return render_template('paciente/plan.html', plan=plan, comidas=comidas)

@app.route('/paciente/perfil', methods=['GET', 'POST'])
@login_required(roles=['Paciente'])
def paciente_perfil():
    """RF11: Consultar y actualizar perfil de paciente (contacto, alergias, metas)."""
    paciente_id = session.get('paciente_id')
    user_id = session.get('user_id')
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        telefono = request.form.get('telefono')
        alergias = request.form.get('alergias')
        objetivo_salud = request.form.get('objetivo_salud')
        password = request.form.get('password')

        cursor.execute("UPDATE usuarios SET telefono = ? WHERE id_usuario = ?", (telefono, user_id))
        if password and len(password.strip()) > 0:
            cursor.execute("UPDATE usuarios SET password = ? WHERE id_usuario = ?", (password.strip(), user_id))

        cursor.execute("""
            UPDATE pacientes 
            SET alergias = ?, objetivo_salud = ?
            WHERE id_paciente = ?
        """, (alergias, objetivo_salud, paciente_id))
        db.commit()

        flash('Tu perfil ha sido actualizado con éxito.', 'success')
        return redirect(url_for('paciente_perfil'))

    cursor.execute("""
        SELECT p.*, u.nombre, u.apellido, u.email, u.telefono
        FROM pacientes p JOIN usuarios u ON p.id_usuario = u.id_usuario
        WHERE p.id_paciente = ?
    """, (paciente_id,))
    perfil = cursor.fetchone()

    return render_template('paciente/perfil.html', perfil=perfil)

if __name__ == '__main__':
    # Ejecución en el puerto 5050 (para evitar conflicto con AirPlay en macOS)
    app.run(debug=True, host='0.0.0.0', port=5050)
