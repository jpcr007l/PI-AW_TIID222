import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "nutricare.db")

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Habilitar soporte de claves foráneas
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Tabla ROLES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id_rol INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_rol TEXT NOT NULL UNIQUE,
        descripcion TEXT
    );
    """)

    # 2. Tabla USUARIOS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
        id_rol INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        apellido TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        telefono TEXT,
        activo INTEGER DEFAULT 1,
        fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_rol) REFERENCES roles (id_rol)
    );
    """)

    # 3. Tabla NUTRIOLOGOS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nutriologos (
        id_nutriologo INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario INTEGER NOT NULL UNIQUE,
        cedula_profesional TEXT NOT NULL,
        especialidad TEXT NOT NULL,
        horario_inicio TEXT DEFAULT '08:00',
        horario_fin TEXT DEFAULT '18:00',
        FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
    );
    """)

    # 4. Tabla PACIENTES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pacientes (
        id_paciente INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario INTEGER NOT NULL UNIQUE,
        fecha_nacimiento DATE,
        sexo TEXT CHECK(sexo IN ('Femenino', 'Masculino', 'Otro')),
        estatura_cm REAL DEFAULT 165.0,
        alergias TEXT DEFAULT 'Ninguna reportada',
        objetivo_salud TEXT DEFAULT 'Mejora de composición corporal',
        FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario) ON DELETE CASCADE
    );
    """)

    # 5. Tabla CITAS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS citas (
        id_cita INTEGER PRIMARY KEY AUTOINCREMENT,
        id_paciente INTEGER NOT NULL,
        id_nutriologo INTEGER NOT NULL,
        fecha_cita DATE NOT NULL,
        hora_cita TEXT NOT NULL,
        motivo TEXT NOT NULL,
        estado TEXT CHECK(estado IN ('Pendiente', 'Confirmada', 'Completada', 'Cancelada')) DEFAULT 'Pendiente',
        fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_paciente) REFERENCES pacientes (id_paciente),
        FOREIGN KEY (id_nutriologo) REFERENCES nutriologos (id_nutriologo)
    );
    """)

    # 6. Tabla CONSULTAS_ANTROPOMETRICAS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS consultas_antropometricas (
        id_consulta INTEGER PRIMARY KEY AUTOINCREMENT,
        id_paciente INTEGER NOT NULL,
        id_nutriologo INTEGER NOT NULL,
        fecha_evaluacion DATE NOT NULL,
        peso_kg REAL NOT NULL,
        imc REAL NOT NULL,
        porcentaje_grasa REAL,
        masa_muscular_kg REAL,
        circunferencia_cintura REAL,
        circunferencia_cadera REAL,
        diagnostico_notas TEXT,
        FOREIGN KEY (id_paciente) REFERENCES pacientes (id_paciente),
        FOREIGN KEY (id_nutriologo) REFERENCES nutriologos (id_nutriologo)
    );
    """)

    # 7. Tabla PLANES_ALIMENTICIOS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planes_alimenticios (
        id_plan INTEGER PRIMARY KEY AUTOINCREMENT,
        id_paciente INTEGER NOT NULL,
        id_nutriologo INTEGER NOT NULL,
        titulo_plan TEXT NOT NULL,
        calorias_totales INTEGER NOT NULL,
        fecha_inicio DATE NOT NULL,
        fecha_fin DATE,
        activo INTEGER DEFAULT 1,
        FOREIGN KEY (id_paciente) REFERENCES pacientes (id_paciente),
        FOREIGN KEY (id_nutriologo) REFERENCES nutriologos (id_nutriologo)
    );
    """)

    # 8. Tabla COMIDAS_DETALLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comidas_detalle (
        id_comida INTEGER PRIMARY KEY AUTOINCREMENT,
        id_plan INTEGER NOT NULL,
        momento TEXT NOT NULL,
        descripcion_alimentos TEXT NOT NULL,
        recomendaciones TEXT,
        FOREIGN KEY (id_plan) REFERENCES planes_alimenticios (id_plan) ON DELETE CASCADE
    );
    """)

    # ------------------ DATOS SEMILLA (SEED DATA) ------------------
    # Roles
    cursor.execute("SELECT COUNT(*) FROM roles;")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
        INSERT INTO roles (id_rol, nombre_rol, descripcion) VALUES (?, ?, ?);
        """, [
            (1, 'Administrador', 'Control total de la clínica, gestión de especialistas y estadísticas'),
            (2, 'Médico', 'Nutriólogo con agenda, registro clínico antropométrico y prescripción de dietas'),
            (3, 'Paciente', 'Usuario que agenda citas, consulta su plan alimenticio y su progreso físico')
        ])

    # Usuarios
    cursor.execute("SELECT COUNT(*) FROM usuarios;")
    if cursor.fetchone()[0] == 0:
        usuarios_data = [
            # Admin
            (1, 1, 'Coordinación', 'Clínica UPQ', 'admin@nutricare.upq.edu.mx', 'admin123', '4421019000', 1),
            # Nutriólogos
            (2, 2, 'Dra. Valeria', 'Mendoza Soto', 'valeria.mendoza@nutricare.upq.edu.mx', 'medico123', '4423456789', 1),
            (3, 2, 'Dr. Carlos', 'Ramos Aguilar', 'carlos.ramos@nutricare.upq.edu.mx', 'medico123', '4429876543', 1),
            # Pacientes
            (4, 3, 'Ana Paula', 'García López', 'ana.garcia@gmail.com', 'paciente123', '4425551122', 1),
            (5, 3, 'Roberto', 'Sánchez Trejo', 'roberto.sanchez@gmail.com', 'paciente123', '4425553344', 1)
        ]
        cursor.executemany("""
        INSERT INTO usuarios (id_usuario, id_rol, nombre, apellido, email, password, telefono, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, usuarios_data)

        # Nutriólogos detalle
        nutriologos_data = [
            (1, 2, 'CED-984321', 'Nutrición Clínica y Deportiva', '08:00', '16:00'),
            (2, 3, 'CED-543219', 'Nutrición Pediátrica y Síndrome Metabólico', '10:00', '18:00')
        ]
        cursor.executemany("""
        INSERT INTO nutriologos (id_nutriologo, id_usuario, cedula_profesional, especialidad, horario_inicio, horario_fin)
        VALUES (?, ?, ?, ?, ?, ?);
        """, nutriologos_data)

        # Pacientes detalle
        pacientes_data = [
            (1, 4, '1998-05-14', 'Femenino', 163.0, 'Intolerancia a la lactosa', 'Pérdida de porcentaje de grasa y tonificación'),
            (2, 5, '1995-11-20', 'Masculino', 178.0, 'Alergia al marisco', 'Aumento de masa muscular (hipertrofia)')
        ]
        cursor.executemany("""
        INSERT INTO pacientes (id_paciente, id_usuario, fecha_nacimiento, sexo, estatura_cm, alergias, objetivo_salud)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, pacientes_data)

        # Citas iniciales
        citas_data = [
            (1, 1, '2026-11-12', '09:00', 'Consulta de control y ajuste de macros', 'Confirmada'),
            (2, 2, '2026-11-13', '11:00', 'Evaluación inicial antropométrica', 'Pendiente'),
            (1, 1, '2026-10-28', '09:00', 'Primera cita diagnóstica', 'Completada')
        ]
        cursor.executemany("""
        INSERT INTO citas (id_paciente, id_nutriologo, fecha_cita, hora_cita, motivo, estado)
        VALUES (?, ?, ?, ?, ?, ?);
        """, citas_data)

        # Consultas Antropométricas iniciales para Ana Paula (id_paciente: 1)
        # 1. Primera consulta hace 3 semanas
        cursor.execute("""
        INSERT INTO consultas_antropometricas 
        (id_paciente, id_nutriologo, fecha_evaluacion, peso_kg, imc, porcentaje_grasa, masa_muscular_kg, circunferencia_cintura, circunferencia_cadera, diagnostico_notas)
        VALUES (1, 1, '2026-10-28', 68.5, 25.78, 29.5, 24.2, 79.0, 102.0, 'Paciente femenina de 28 años. Presenta sobrepeso leve. Refiere fatiga vespertina y consumo elevado de azúcares refinados.');
        """)

        # 2. Segunda consulta hace 1 semana (mostrando avance)
        cursor.execute("""
        INSERT INTO consultas_antropometricas 
        (id_paciente, id_nutriologo, fecha_evaluacion, peso_kg, imc, porcentaje_grasa, masa_muscular_kg, circunferencia_cintura, circunferencia_cadera, diagnostico_notas)
        VALUES (1, 1, '2026-11-04', 66.8, 25.14, 28.1, 24.5, 76.5, 100.5, 'Excelente adherencia al plan normocalórico. Reducción de 1.7 kg de peso y descenso de 1.4% de grasa corporal manteniendo masa magra.');
        """)

        # Plan alimenticio activo para Ana Paula
        cursor.execute("""
        INSERT INTO planes_alimenticios (id_plan, id_paciente, id_nutriologo, titulo_plan, calorias_totales, fecha_inicio, fecha_fin, activo)
        VALUES (1, 1, 1, 'Plan de Recomposición y Balance Metabólico', 1850, '2026-11-04', '2026-11-25', 1);
        """)

        # Comidas detalle
        comidas = [
            (1, 'Desayuno (08:00 hrs)', '2 huevos al gusto con espinacas y jitomate, 1 rebanada de pan integral, 1/3 de aguacate y café o té sin azúcar.', 'Consumir agua natural antes de iniciar el desayuno.'),
            (1, 'Colación Matutina (11:30 hrs)', '1 manzana verde en rodajas con 1 cucharada de crema de cacahuate sin azúcar añadida y 5 almendras.', 'Ideal para mantener energía estable.'),
            (1, 'Comida (14:30 hrs)', '130g de pechuga de pollo o filete de pescado a la plancha, 1 taza de arroz integral o quinoa al vapor, ensalada verde abundante (lechuga, pepino, limón) y aderezo de 1 cda de aceite de oliva.', 'Evitar bebidas azucaradas, hidratarse con agua de jamaica o limón con chía sin azúcar.'),
            (1, 'Colación Vespertina (17:30 hrs)', '1 taza de yogurt griego natural sin grasa ni azúcar con 1/2 taza de frutos rojos (fresas o arándanos).', 'Aporte proteico previo a la rutina de ejercicio.'),
            (1, 'Cena (20:30 hrs)', '2 tostadas horneadas de maíz con atún en agua (1 lata), pico de gallo y rebanadas de aguacate.', 'Cenar al menos 1.5 horas antes de acostarse a dormir.')
        ]
        cursor.executemany("""
        INSERT INTO comidas_detalle (id_plan, momento, descripcion_alimentos, recomendaciones)
        VALUES (?, ?, ?, ?);
        """, comidas)

    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente con datos semilla.")

if __name__ == '__main__':
    init_database()
