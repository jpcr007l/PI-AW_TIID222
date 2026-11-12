# NutriCare UPQ 🥗

**Sistema Web de Gestión de Consultas de Nutrición**
Universidad Politécnica de Querétaro — Materia: Aplicaciones Web

---

## Descripción
Aplicación web desarrollada con Flask (Python) y DaisyUI para el control de citas, consultas y expedientes de pacientes en un consultorio de nutrición.

**3 Roles de usuario:** Administrador | Médico (Nutriólogo) | Paciente

## Tecnologías
- **Backend:** Python 3 + Flask
- **Frontend:** DaisyUI 4 + Tailwind CSS (CDN)
- **Base de Datos:** SQLite 3
- **Editor:** Visual Studio Code

## Cómo correrlo

```bash
cd nutricare-upq
python -m venv venv
source venv/bin/activate       # Mac/Linux
pip install flask
python init_db.py              # Inicializar BD con datos de prueba
python app.py                  # Correr servidor en puerto 5050
```

Abrir en el navegador: **http://localhost:5050**

### Cuentas de prueba
| Rol | Correo | Contraseña |
|-----|--------|-----------|
| Administrador | admin@nutricare.com | admin123 |
| Médico | medico@nutricare.com | medico123 |
| Paciente | paciente@nutricare.com | paciente123 |

## Alumno
**Haziel Joseph Cornejo Silva** — 125053461@upq.edu.mx — TIID 4to Cuatrimestre
