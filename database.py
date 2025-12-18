import streamlit as st
import psycopg2
import datetime
from decimal import Decimal

# ==========================================
# 🔌 CONEXIÓN
# ==========================================
def connect_db():
    db_url = st.secrets.get("DATABASE_URL")
    if not db_url:
        import os
        db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("❌ No se encontró DATABASE_URL.")
    return psycopg2.connect(db_url)

# ==========================================
# 🛠️ CREACIÓN DE TABLAS
# ==========================================
def create_all_tables():
    conn = connect_db(); cur = conn.cursor()
    
    cur.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL);")
    cur.execute("CREATE TABLE IF NOT EXISTS fincas (id SERIAL PRIMARY KEY, nombre TEXT NOT NULL, owner TEXT NOT NULL);")
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trabajadores (
            id SERIAL PRIMARY KEY, nombre_completo TEXT NOT NULL,
            tipo TEXT DEFAULT 'Jornalero', owner TEXT NOT NULL
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jornadas (
            id SERIAL PRIMARY KEY, trabajador TEXT, fecha DATE, lote TEXT,
            actividad TEXT, dias NUMERIC, horas_normales NUMERIC,
            horas_extra NUMERIC, owner TEXT
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS insumos (
            id SERIAL PRIMARY KEY, fecha DATE, lote TEXT, tipo TEXT,
            etapa TEXT, producto TEXT, dosis TEXT, cantidad NUMERIC,
            precio_unitario NUMERIC,
            costo_total NUMERIC GENERATED ALWAYS AS (cantidad * precio_unitario) STORED,
            owner TEXT
        );
    """)
    
    cur.execute("CREATE TABLE IF NOT EXISTS tarifas (owner TEXT PRIMARY KEY, pago_dia NUMERIC DEFAULT 0, pago_hora_extra NUMERIC DEFAULT 0);")
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS planes (
            id SERIAL PRIMARY KEY, fecha DATE, lote TEXT, tipo TEXT,
            trabajador TEXT, actividad TEXT, etapa TEXT, producto TEXT,
            dosis TEXT, cantidad NUMERIC, precio_unitario NUMERIC,
            dias NUMERIC, horas_extra NUMERIC, estado TEXT DEFAULT 'pendiente',
            recur_every_days INTEGER, recur_times INTEGER,
            recur_autorenew BOOLEAN DEFAULT FALSE, owner TEXT
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cierres_mensuales (
            id SERIAL PRIMARY KEY, mes_inicio DATE, mes_fin DATE,
            creado_por TEXT, fecha_creacion TIMESTAMP DEFAULT NOW(),
            total_nomina NUMERIC, total_insumos NUMERIC, total_general NUMERIC, owner TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS recolecciones (
            id SERIAL PRIMARY KEY, fecha DATE, trabajador TEXT, lote TEXT,
            cajuelas NUMERIC, precio_cajuela NUMERIC,
            total_pagar NUMERIC GENERATED ALWAYS AS (cajuelas * precio_cajuela) STORED,
            owner TEXT
        );
    """)
    conn.commit(); cur.close(); conn.close()

# ==========================================
# 🔐 AUTH & BASIC CRUD
# ==========================================
def verify_user(username, password):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username = %s", (username,))
    res = cur.fetchone(); conn.close()
    return res and res[0] == password

def add_user(username, password):
    try:
        conn = connect_db(); cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        conn.commit(); conn.close(); return True
    except: return False

def get_all_fincas(owner):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("SELECT nombre FROM fincas WHERE owner = %s ORDER BY nombre", (owner,))
    data = [row[0] for row in cur.fetchall()]; conn.close(); return data

def add_finca(nombre, owner):
    if nombre in get_all_fincas(owner): return False
    conn = connect_db(); cur = conn.cursor()
    cur.execute("INSERT INTO fincas (nombre, owner) VALUES (%s, %s)", (nombre, owner))
    conn.commit(); conn.close(); return True

def delete_finca(nombre, owner):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("DELETE FROM fincas WHERE nombre = %s AND owner = %s", (nombre, owner))
    deleted = cur.rowcount > 0; conn.commit(); conn.close(); return deleted

# ==========================================
# 👥 TRABAJADORES
# ==========================================
def get_all_trabajadores(owner):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("SELECT nombre_completo FROM trabajadores WHERE owner = %s ORDER BY nombre_completo", (owner,))
    data = [row[0] for row in cur.fetchall()]; conn.close(); return data

def get_trabajadores_por_tipo(owner, tipo):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("SELECT nombre_completo FROM trabajadores WHERE owner = %s AND tipo = %s ORDER BY nombre_completo", (owner, tipo))
    data = [row[0] for row in cur.fetchall()]; conn.close(); return data

def add_trabajador(nombre, apellido, tipo, owner):
    full = f"{nombre} {apellido}".strip()
    conn = connect_db(); cur = conn.cursor()
    cur.execute("INSERT INTO trabajadores (nombre_completo, tipo, owner) VALUES (%s, %s, %s)", (full, tipo, owner))
    conn.commit(); conn.close(); return True

def delete_trabajador_by_fullname(owner, fullname):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("DELETE FROM trabajadores WHERE nombre_completo = %s AND owner = %s", (fullname, owner))
    deleted = cur.rowcount > 0; conn.commit(); conn.close(); return deleted

# ==========================================
# 💰 TARIFAS Y JORNADAS
# ==========================================
def get_tarifas(owner):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("SELECT pago_dia, pago_hora_extra FROM tarifas WHERE owner = %s", (owner,))
    res = cur.fetchone(); conn.close()
    if res: return float(res[0]), float(res[1])
    return (0.0, 0.0)

def set_tarifas(owner, dia, extra):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO tarifas (owner, pago_dia, pago_hora_extra) VALUES (%s, %s, %s)
        ON CONFLICT (owner) DO UPDATE SET pago_dia = EXCLUDED.pago_dia, pago_hora_extra = EXCLUDED.pago_hora_extra;
    """, (owner, dia, extra))
    conn.commit(); conn.close()

def add_jornada(trab, fecha, lote, act, dias, hnorm, hextra, owner):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("INSERT INTO jornadas (trabajador, fecha, lote, actividad, dias, horas_normales, horas_extra, owner) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (trab, fecha, lote, act, dias, hnorm, hextra, owner))
    conn.commit(); conn.close()

def get_all_jornadas(owner):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("SELECT id, trabajador, fecha, lote, actividad, dias, horas_normales, horas_extra FROM jornadas WHERE owner = %s ORDER BY fecha DESC", (owner,))
    data = cur.fetchall(); conn.close(); return data

def get_jornadas_between(ini, fin, owner):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("SELECT id, trabajador, fecha, lote, actividad, dias, horas_normales, horas_extra FROM jornadas WHERE owner=%s AND fecha >= %s AND fecha <= %s", (owner, ini, fin))
    res = cur.fetchall(); conn.close(); return res

def get_last_jornada_by_date(fecha, owner):
    conn = connect_db(); cur = conn.cursor()
    # CORREGIDO: Se agregó 'owner' al SELECT para evitar errores de índice en app.py
    cur.execute("SELECT id, owner, trabajador, fecha, lote, actividad, dias, horas_normales, horas_extra FROM jornadas WHERE owner=%s AND fecha=%s ORDER BY id DESC LIMIT 1", (owner, fecha))
    res = cur.fetchone(); conn.close(); return res

def update_jornada(jid, trab, fecha, lote, act, dias, hnorm, hextra, owner):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("UPDATE jornadas SET trabajador=%s, fecha=%s, lote=%s, actividad=%s, dias=%s, horas_normales=%s, horas_extra=%s WHERE id=%s AND owner=%s", (trab, fecha, lote, act, dias, hnorm, hextra, jid, owner))
    conn.commit(); conn.close()

# ==========================================
# 📦 INSUMOS
# ==========================================
def add_insumo(fecha, lote, tipo, etapa, prod, dosis, cant, precio, owner):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("INSERT INTO insumos (fecha, lote, tipo, etapa, producto, dosis, cantidad, precio_unitario, owner) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (fecha, lote, tipo, etapa, prod, dosis, cant, precio, owner))
    conn.commit(); conn.close()

def get_insumos_between(ini, fin, owner):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("SELECT id, fecha, lote, tipo, etapa, producto, dosis, cantidad, precio_unitario, costo_total FROM insumos WHERE owner=%s AND fecha >= %s AND fecha <= %s", (owner, ini, fin))
    res = cur.fetchall(); conn.close(); return res

# ==========================================
# 🗓️ PLANIFICADOR
# ==========================================
def add_plan(owner, fecha, lote, tipo, **kwargs):
    conn = connect_db(); cur = conn.cursor()
    cols = ["owner", "fecha", "lote", "tipo", "estado"]
    vals = [owner, fecha, lote, tipo, "pendiente"]
    posibles = ["trabajador", "actividad", "etapa", "producto", "dosis", "cantidad", "precio_unitario", "dias", "horas_extra", "recur_every_days", "recur_times", "recur_autorenew"]
    for k in posibles:
        if k in kwargs and kwargs[k] is not None:
            cols.append(k); vals.append(kwargs[k])
    q = f"INSERT INTO planes ({','.join(cols)}) VALUES ({','.join(['%s']*len(vals))})"
    cur.execute(q, tuple(vals)); conn.commit(); conn.close()

def list_plans(owner, ini, fin):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("SELECT id, fecha, lote, tipo, trabajador, actividad, etapa, producto, dosis, cantidad, precio_unitario, dias, horas_extra, estado, recur_every_days, recur_times, recur_autorenew FROM planes WHERE owner=%s AND fecha >= %s AND fecha <= %s ORDER BY fecha ASC", (owner, ini, fin))
    res = cur.fetchall(); conn.close(); return res

def mark_plan_done_and_autorenew(owner, pid, user):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("UPDATE planes SET estado='realizado' WHERE id=%s AND owner=%s RETURNING recur_autorenew, recur_every_days, recur_times, fecha", (pid, owner))
    res = cur.fetchone()
    if res and res[0] and res[1]:
        autorenew, days, times, old_date = res
        if times is None or times > 1:
            new_date = old_date + datetime.timedelta(days=days)
            new_times = times - 1 if times else None
            cur.execute("INSERT INTO planes (fecha, lote, tipo, trabajador, actividad, etapa, producto, dosis, cantidad, precio_unitario, dias, horas_extra, estado, recur_every_days, recur_times, recur_autorenew, owner) SELECT %s, lote, tipo, trabajador, actividad, etapa, producto, dosis, cantidad, precio_unitario, dias, horas_extra, 'pendiente', recur_every_days, %s, recur_autorenew, owner FROM planes WHERE id=%s", (new_date, new_times, pid))
    conn.commit(); conn.close()

def postpone_plan(owner, pid, days):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("UPDATE planes SET fecha = fecha + make_interval(days => %s) WHERE id=%s AND owner=%s", (int(days), pid, owner))
    conn.commit(); conn.close()

# ==========================================
# ☕ COSECHA
# ==========================================
def add_recoleccion_batch(datos_lista):
    conn = connect_db(); cur = conn.cursor()
    try:
        args_str = ','.join(cur.mogrify("(%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in datos_lista)
        cur.execute("INSERT INTO recolecciones (fecha, trabajador, lote, cajuelas, precio_cajuela, owner) VALUES " + args_str)
        conn.commit(); return True
    except Exception as e: return False
    finally: conn.close()

def get_reporte_cosecha_detallado(ini, fin, owner):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("SELECT trabajador, lote, SUM(cajuelas) as total_cajuelas, SUM(total_pagar) as total_dinero FROM recolecciones WHERE owner=%s AND fecha >= %s AND fecha <= %s GROUP BY trabajador, lote ORDER BY trabajador, lote", (owner, ini, fin))
    res = cur.fetchall(); conn.close(); return res

def get_totales_por_lote(ini, fin, owner):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("SELECT lote, SUM(cajuelas) FROM recolecciones WHERE owner=%s AND fecha >= %s AND fecha <= %s GROUP BY lote ORDER BY SUM(cajuelas) DESC", (owner, ini, fin))
    res = cur.fetchall(); conn.close(); return res

def crear_cierre_mensual(ini, fin, creado_por, owner, tarifa_dia, tarifa_hora_extra, overwrite=False):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("INSERT INTO cierres_mensuales (mes_inicio, mes_fin, creado_por, owner) VALUES (%s, %s, %s, %s) RETURNING id", (ini, fin, creado_por, owner))
    pid = cur.fetchone()[0]; conn.commit(); conn.close(); return pid

def listar_cierres(owner):
    conn = connect_db(); cur = conn.cursor()
    cur.execute("SELECT id, mes_inicio, mes_fin, creado_por, fecha_creacion, total_nomina, total_insumos, total_general FROM cierres_mensuales WHERE owner=%s ORDER BY id DESC", (owner,))
    res = cur.fetchall(); conn.close(); return res