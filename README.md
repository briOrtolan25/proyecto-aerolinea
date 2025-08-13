# ✈ Aerolíneas Aurora – Sistema de Gestión con Django

Este proyecto es un sistema para la gestión de **aviones, vuelos, asientos, pasajeros, reservas y boletos** desarrollado con **Django**.

---

## 📌 Requisitos previos

- Python 3.12 o superior
- pip (gestor de paquetes de Python)
- Virtualenv (recomendado)
- SQLite (incluido en Python)

---

## 🚀 Instalación y configuración

### 1️⃣ Crear carpeta de trabajo y entrar en ella
```bash
mkdir aerolineas-aurora
cd aerolineas-aurora

# Crear entorno virtual
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

# Instalar Django
pip install django

# Crear proyecto y aplicación
django-admin startproject proyecto_aerolinea .
python manage.py startapp gestion

# Migraciones iniciales
python manage.py makemigrations
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Si hubo errores de migraciones o cambios en modelos:
rm db.sqlite3
rm gestion/migrations/0*.py
python manage.py makemigrations
python manage.py migrate

# Entrar a la shell de Django
python manage.py shell

# Ejecutar el servidor
python manage.py runserver
