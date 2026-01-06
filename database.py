import os
import logging
import logging
import datetime
import contextlib
from decimal import Decimal

import streamlit as st
import psycopg2
from psycopg2 import pool
import bcrypt

logger = logging.getLogger(__name__)

# ==========================================
# 🔌 CONEXIÓN & POOLING (OPTIMIZADO)
# ==========================================

@st.cache_resource
def get_connection_pool():
    """
    Crea un pool de conexiones persistente. 
    Evita reconectar con Supabase en cada consulta.
    """
    try:
        # 1. Obtener URL
        db_url = st.secrets.get("DATABASE_URL")
        if not db_url:
            db_url = os.getenv("DATABASE_URL")
        
        if not db_url:
            raise ValueError("❌ No se encontró DATABASE_URL en secrets o env.")

        # 2. Crear Pool (Min 1, Max 10 conexiones)
        return psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=db_url,
            connect_timeout=5,
            sslmode='require' # Requerido por Supabase
        )
    except psycopg2.Error as e:
        logger.error(f"Error fatal creando Pool de DB: {e}")
        st.error("Error de conexión a la Base de Datos. Revise los logs.")
        return None

@contextlib.contextmanager
def get_db_cursor():
    """
    Context manager que pide una conexión prestada al pool, 
    entrega el cursor, y devuelve la conexión al terminar.
    """
    connection_pool = get_connection_pool()
    if connection_pool is None:
        raise Exception("No hay conexión a la base de datos (Pool falló).")

    conn = None
    try:
        # Pedir conexión prestada
        conn = connection_pool.getconn()
        
        # Si la conexión se murió por inactividad, pedir otra
        if conn.closed:
            connection_pool.putconn(conn, close=True)
            conn = connection_pool.getconn()

        cur = conn.cursor()
        try:
            yield cur, conn
            # Nota: El commit lo hace la función que llama, no aquí automáticamente.
        except psycopg2.Error as e:
            conn.rollback()
            logger.exception("Error SQL: %s", e)
            raise
        except Exception as e:
            conn.rollback()
            logger.exception("Error General DB: %s", e)
            raise
        finally:
            cur.close()
    finally:
        # Devolver conexión al pool (IMPORTANTE)
        if conn:
            try:
                connection_pool.putconn(conn)
            except Exception:
                pass # Si falla devolverla, el pool la reciclará eventualmente

# ==========================================
# 🛠️ CREACIÓN DE TABLAS (AUTO-MANTENIMIENTO)
# ==========================================

def create_all_tables():
    """Crea tablas y ejecuta migraciones ligeras."""
    with get_db_cursor() as (cur, conn):
        # --- USUARIOS ---
        cur.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL);")

        # --- FINCAS & MAPAS ---
        cur.execute("CREATE TABLE IF NOT EXISTS fincas (id SERIAL PRIMARY KEY, nombre TEXT NOT NULL, owner TEXT NOT NULL);")
        
        # Migración Columnas Mapa
        try:
            cur.execute("ALTER TABLE fincas ADD COLUMN IF NOT EXISTS latitud NUMERIC DEFAULT 0.0")
            cur.execute("ALTER TABLE fincas ADD COLUMN IF NOT EXISTS longitud NUMERIC DEFAULT 0.0")
            cur.execute("ALTER TABLE fincas ADD COLUMN IF NOT EXISTS poligono_geojson TEXT")
            conn.commit()
        except psycopg2.Error:
            conn.rollback()

        # --- PERSONAL ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trabajadores (
                id SERIAL PRIMARY KEY, nombre_completo TEXT NOT NULL,
                tipo TEXT DEFAULT 'Jornalero', owner TEXT NOT NULL
            );
        """)

        # --- OPERATIVAS ---
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

        cur.execute("""
            CREATE TABLE IF NOT EXISTS vales (
                id SERIAL PRIMARY KEY, fecha DATE, trabajador TEXT,
                monto NUMERIC, concepto TEXT, owner TEXT
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS analisis_suelo (
                id SERIAL PRIMARY KEY, fecha DATE, lote TEXT,
                ph NUMERIC, nitrogeno NUMERIC, fosforo NUMERIC, potasio NUMERIC,
                notas TEXT, owner TEXT
            );
        """)

        # --- CATÁLOGOS ---
        cur.execute("CREATE TABLE IF NOT EXISTS catalogo_productos (id SERIAL PRIMARY KEY, nombre TEXT NOT NULL, owner TEXT NOT NULL);")
        cur.execute("CREATE TABLE IF NOT EXISTS catalogo_labores (id SERIAL PRIMARY KEY, nombre TEXT NOT NULL, owner TEXT NOT NULL);")

        conn.commit()


# ==========================================
# 🔐 USUARIOS & SEGURIDAD (ACTUALIZADO)
# ==========================================

def verify_user(username, password):
    """Verifica credenciales usando bcrypt."""
    with get_db_cursor() as (cur, conn):
        cur.execute("SELECT password FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        if not row:
            return False
        stored = row[0]
        
        # BCrypt Check
        if isinstance(stored, str) and stored.startswith("$2"):
            try:
                return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
            except:
                return False
        
        # Migración automática de contraseñas viejas (texto plano a bcrypt)
        if stored == password:
            try:
                hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                cur.execute("UPDATE users SET password=%s WHERE username=%s", (hashed, username))
                conn.commit()
            except:
                conn.rollback()
            return True
        return False


def create_user(username, password):
    """Crea un usuario nuevo con contraseña encriptada. Retorna (Bool, Mensaje)."""
    try:
        with get_db_cursor() as (cur, conn):
            # 1. Verificar si existe
            cur.execute("SELECT username FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                return False, "⚠️ El usuario ya existe. Intenta con otro."

            # 2. Encriptar
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            
            # 3. Insertar
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
            conn.commit()
            return True, "✅ Usuario creado exitosamente."
    except psycopg2.Error as e:
        return False, f"❌ Error de base de datos: {e}"
    except Exception as e:
        return False, f"❌ Error inesperado: {e}"


# ==========================================
# 🚜 GESTIÓN DE FINCAS & CATÁLOGOS
# ==========================================

def get_all_fincas(owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT nombre FROM fincas WHERE owner = %s ORDER BY nombre", (owner,))
        return [row[0] for row in cur.fetchall()]

def add_finca(nombre, owner):
    if nombre in get_all_fincas(owner):
        return False
    with get_db_cursor() as (cur, conn):
        cur.execute("INSERT INTO fincas (nombre, owner) VALUES (%s, %s)", (nombre, owner))
        conn.commit()
        return True

def delete_finca(nombre, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("DELETE FROM fincas WHERE nombre = %s AND owner = %s", (nombre, owner))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted

def get_catalogo_productos(owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT nombre FROM catalogo_productos WHERE owner = %s ORDER BY nombre", (owner,))
        return [row[0] for row in cur.fetchall()]

def add_catalogo_producto(nombre, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("SELECT id FROM catalogo_productos WHERE nombre=%s AND owner=%s", (nombre, owner))
        if cur.fetchone(): return False
        cur.execute("INSERT INTO catalogo_productos (nombre, owner) VALUES (%s, %s)", (nombre, owner))
        conn.commit()
        return True

def delete_catalogo_producto(nombre, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("DELETE FROM catalogo_productos WHERE nombre=%s AND owner=%s", (nombre, owner))
        conn.commit()

def get_catalogo_labores(owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT nombre FROM catalogo_labores WHERE owner = %s ORDER BY nombre", (owner,))
        return [row[0] for row in cur.fetchall()]

def add_catalogo_labor(nombre, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("SELECT id FROM catalogo_labores WHERE nombre=%s AND owner=%s", (nombre, owner))
        if cur.fetchone(): return False
        cur.execute("INSERT INTO catalogo_labores (nombre, owner) VALUES (%s, %s)", (nombre, owner))
        conn.commit()
        return True

def delete_catalogo_labor(nombre, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("DELETE FROM catalogo_labores WHERE nombre=%s AND owner=%s", (nombre, owner))
        conn.commit()


# ==========================================
# 👥 PERSONAL & VALES
# ==========================================

def get_all_trabajadores(owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT nombre_completo FROM trabajadores WHERE owner = %s ORDER BY nombre_completo", (owner,))
        return [row[0] for row in cur.fetchall()]

def get_trabajadores_por_tipo(owner, tipo):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT nombre_completo FROM trabajadores WHERE owner = %s AND tipo = %s ORDER BY nombre_completo", (owner, tipo))
        return [row[0] for row in cur.fetchall()]

def add_trabajador(nombre, apellido, tipo, owner):
    full = f"{nombre} {apellido}".strip()
    with get_db_cursor() as (cur, conn):
        cur.execute("INSERT INTO trabajadores (nombre_completo, tipo, owner) VALUES (%s, %s, %s)", (full, tipo, owner))
        conn.commit()
        return True

def delete_trabajador_by_fullname(owner, fullname):
    with get_db_cursor() as (cur, conn):
        cur.execute("DELETE FROM trabajadores WHERE nombre_completo = %s AND owner = %s", (fullname, owner))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted

def add_vale(fecha, trabajador, monto, concepto, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("INSERT INTO vales (fecha, trabajador, monto, concepto, owner) VALUES (%s, %s, %s, %s, %s)",
            (fecha, trabajador, monto, concepto, owner))
        conn.commit()

def get_saldo_global(owner):
    """Retorna {trabajador: total_vales}"""
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT trabajador, SUM(monto) FROM vales WHERE owner=%s GROUP BY trabajador", (owner,))
        return {row[0]: float(row[1]) for row in cur.fetchall()}


# ==========================================
# 💰 TARIFAS Y JORNADAS
# ==========================================

def get_tarifas(owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT pago_dia, pago_hora_extra FROM tarifas WHERE owner = %s", (owner,))
        res = cur.fetchone()
        if res: return float(res[0]), float(res[1])
        return (0.0, 0.0)

def set_tarifas(owner, dia, extra):
    with get_db_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO tarifas (owner, pago_dia, pago_hora_extra) VALUES (%s, %s, %s)
            ON CONFLICT (owner) DO UPDATE SET pago_dia = EXCLUDED.pago_dia, pago_hora_extra = EXCLUDED.pago_hora_extra;
        """, (owner, dia, extra))
        conn.commit()

def add_jornada(trab, fecha, lote, act, dias, hnorm, hextra, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("""
            INSERT INTO jornadas (trabajador, fecha, lote, actividad, dias, horas_normales, horas_extra, owner) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (trab, fecha, lote, act, dias, hnorm, hextra, owner))
        conn.commit()

def get_all_jornadas(owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT id, trabajador, fecha, lote, actividad, dias, horas_normales, horas_extra FROM jornadas WHERE owner = %s ORDER BY fecha DESC", (owner,))
        return cur.fetchall()

def get_jornadas_between(ini, fin, owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT id, trabajador, fecha, lote, actividad, dias, horas_normales, horas_extra FROM jornadas WHERE owner=%s AND fecha >= %s AND fecha <= %s",
            (owner, ini, fin))
        return cur.fetchall()

def update_jornada(jid, trab, fecha, lote, act, dias, hnorm, hextra, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("UPDATE jornadas SET trabajador=%s, fecha=%s, lote=%s, actividad=%s, dias=%s, horas_normales=%s, horas_extra=%s WHERE id=%s AND owner=%s",
            (trab, fecha, lote, act, dias, hnorm, hextra, jid, owner))
        conn.commit()


# ==========================================
# 📦 INSUMOS & SUELOS
# ==========================================

def add_insumo(fecha, lote, tipo, etapa, prod, dosis, cant, precio, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("INSERT INTO insumos (fecha, lote, tipo, etapa, producto, dosis, cantidad, precio_unitario, owner) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (fecha, lote, tipo, etapa, prod, dosis, cant, precio, owner))
        conn.commit()

def get_insumos_between(ini, fin, owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT id, fecha, lote, tipo, etapa, producto, dosis, cantidad, precio_unitario, costo_total FROM insumos WHERE owner=%s AND fecha >= %s AND fecha <= %s",
            (owner, ini, fin))
        return cur.fetchall()

def add_analisis_suelo(fecha, lote, ph, n, p, k, notas, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("INSERT INTO analisis_suelo (fecha, lote, ph, nitrogeno, fosforo, potasio, notas, owner) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (fecha, lote, ph, n, p, k, notas, owner))
        conn.commit()

def get_analisis_suelo(owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT id, fecha, lote, ph, nitrogeno, fosforo, potasio, notas FROM analisis_suelo WHERE owner=%s ORDER BY fecha DESC", (owner,))
        return cur.fetchall()


# ==========================================
# 🗓️ PLANIFICADOR
# ==========================================

def add_plan(owner, fecha, lote, tipo, **kwargs):
    with get_db_cursor() as (cur, conn):
        cols = ["owner", "fecha", "lote", "tipo", "estado"]
        vals = [owner, fecha, lote, tipo, "pendiente"]
        posibles = ["trabajador", "actividad", "etapa", "producto", "dosis", "cantidad", "precio_unitario", 
                    "dias", "horas_extra", "recur_every_days", "recur_times", "recur_autorenew"]
        for k in posibles:
            if k in kwargs and kwargs[k] is not None:
                cols.append(k)
                vals.append(kwargs[k])
        q = f"INSERT INTO planes ({','.join(cols)}) VALUES ({','.join(['%s']*len(vals))})"
        cur.execute(q, tuple(vals))
        conn.commit()

def list_plans(owner, ini, fin):
    with get_db_cursor() as (cur, _):
        cur.execute("""SELECT id, fecha, lote, tipo, trabajador, actividad, etapa, producto, dosis, cantidad, precio_unitario, dias, horas_extra, estado, recur_every_days, recur_times, recur_autorenew 
                       FROM planes WHERE owner=%s AND fecha >= %s AND fecha <= %s ORDER BY fecha ASC""", (owner, ini, fin))
        return cur.fetchall()

def get_plan_by_id(pid, owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT id, fecha, lote, tipo, trabajador, actividad, producto, cantidad FROM planes WHERE id=%s AND owner=%s", (pid, owner))
        return cur.fetchone()

def update_plan_simple(pid, fecha, lote, tipo, trab, act, prod, cant, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("UPDATE planes SET fecha=%s, lote=%s, tipo=%s, trabajador=%s, actividad=%s, producto=%s, cantidad=%s WHERE id=%s AND owner=%s",
            (fecha, lote, tipo, trab, act, prod, cant, pid, owner))
        conn.commit()

def delete_plan(pid, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("DELETE FROM planes WHERE id=%s AND owner=%s", (pid, owner))
        conn.commit()

def mark_plan_done_and_autorenew(owner, pid, user):
    with get_db_cursor() as (cur, conn):
        cur.execute("UPDATE planes SET estado='realizado' WHERE id=%s AND owner=%s RETURNING recur_autorenew, recur_every_days, recur_times, fecha", (pid, owner))
        res = cur.fetchone()
        if res and res[0] and res[1]:
            autorenew, days, times, old_date = res
            if times is None or times > 1:
                new_date = old_date + datetime.timedelta(days=days)
                new_times = times - 1 if times else None
                cur.execute("""
                    INSERT INTO planes (fecha, lote, tipo, trabajador, actividad, etapa, producto, dosis, cantidad, precio_unitario, dias, horas_extra, estado, recur_every_days, recur_times, recur_autorenew, owner) 
                    SELECT %s, lote, tipo, trabajador, actividad, etapa, producto, dosis, cantidad, precio_unitario, dias, horas_extra, 'pendiente', recur_every_days, %s, recur_autorenew, owner FROM planes WHERE id=%s
                """, (new_date, new_times, pid))
        conn.commit()

def postpone_plan(owner, pid, days):
    with get_db_cursor() as (cur, conn):
        cur.execute("UPDATE planes SET fecha = fecha + make_interval(days => %s) WHERE id=%s AND owner=%s", (int(days), pid, owner))
        conn.commit()


# ==========================================
# ☕ COSECHA & REPORTES
# ==========================================

def add_recoleccion_batch(datos_lista):
    """Inserta múltiples recolecciones en una sola transacción."""
    with get_db_cursor() as (cur, conn):
        try:
            args_str = ",".join(cur.mogrify("(%s,%s,%s,%s,%s,%s)", x).decode("utf-8") for x in datos_lista)
            cur.execute("INSERT INTO recolecciones (fecha, trabajador, lote, cajuelas, precio_cajuela, owner) VALUES " + args_str)
            conn.commit()
            return True
        except psycopg2.Error as e:
            conn.rollback()
            logger.exception("Error batch cosecha: %s", e)
            return False

def get_reporte_cosecha_detallado(ini, fin, owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT trabajador, lote, SUM(cajuelas) as total_cajuelas, SUM(total_pagar) as total_dinero FROM recolecciones WHERE owner=%s AND fecha >= %s AND fecha <= %s GROUP BY trabajador, lote ORDER BY trabajador, lote",
            (owner, ini, fin))
        return cur.fetchall()

def get_totales_por_lote(ini, fin, owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT lote, SUM(cajuelas) FROM recolecciones WHERE owner=%s AND fecha >= %s AND fecha <= %s GROUP BY lote ORDER BY SUM(cajuelas) DESC",
            (owner, ini, fin))
        return cur.fetchall()

def get_produccion_total_lote(owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT lote, SUM(cajuelas) FROM recolecciones WHERE owner=%s GROUP BY lote", (owner,))
        return {row[0]: float(row[1]) for row in cur.fetchall()}


# ==========================================
# 📊 FINANZAS & CIERRES (Optimizado)
# ==========================================

def get_gastos_por_lote(owner):
    """Calcula gastos acumulados por lote de forma eficiente."""
    with get_db_cursor() as (cur, _):
        # 1. Insumos (usando COALESCE para evitar None)
        cur.execute("SELECT lote, COALESCE(SUM(costo_total), 0) FROM insumos WHERE owner=%s GROUP BY lote", (owner,))
        g_insumos = {row[0]: float(row[1]) for row in cur.fetchall()}

        # 2. Mano de Obra
        cur.execute("SELECT pago_dia FROM tarifas WHERE owner=%s", (owner,))
        res_t = cur.fetchone()
        tarifa = float(res_t[0]) if res_t else 0.0

        cur.execute("SELECT lote, COALESCE(SUM(dias), 0) FROM jornadas WHERE owner=%s GROUP BY lote", (owner,))
        g_jornales = {row[0]: float(row[1]) * tarifa for row in cur.fetchall()}

        todos_lotes = set(g_insumos.keys()) | set(g_jornales.keys())
        resultado = []
        for l in todos_lotes:
            i_val = g_insumos.get(l, 0.0)
            j_val = g_jornales.get(l, 0.0)
            resultado.append({
                "Lote": l,
                "Insumos": i_val,
                "ManoObra": j_val,
                "TotalGasto": i_val + j_val,
            })
        return sorted(resultado, key=lambda x: x["TotalGasto"], reverse=True)

def calcular_resumen_periodo(ini, fin, owner):
    """Resumen rápido para el Dashboard y Cierres."""
    with get_db_cursor() as (cur, _):
        # Tres consultas simples en vez de una compleja
        cur.execute("SELECT COALESCE(SUM(total_pagar), 0) FROM recolecciones WHERE owner=%s AND fecha BETWEEN %s AND %s", (owner, ini, fin))
        total_cosecha = float(cur.fetchone()[0])

        cur.execute("SELECT COALESCE(SUM(costo_total), 0) FROM insumos WHERE owner=%s AND fecha BETWEEN %s AND %s", (owner, ini, fin))
        total_insumos = float(cur.fetchone()[0])

        cur.execute("SELECT pago_dia, pago_hora_extra FROM tarifas WHERE owner=%s", (owner,))
        t_res = cur.fetchone()
        t_dia, t_extra = (float(t_res[0]), float(t_res[1])) if t_res else (0.0, 0.0)

        cur.execute("SELECT COALESCE(SUM(dias), 0), COALESCE(SUM(horas_extra), 0) FROM jornadas WHERE owner=%s AND fecha BETWEEN %s AND %s", (owner, ini, fin))
        j_res = cur.fetchone()
        dias_tot, extras_tot = float(j_res[0]), float(j_res[1])
        total_mano_obra = (dias_tot * t_dia) + (extras_tot * t_extra)

        return {
            "Cosecha": total_cosecha,
            "Insumos": total_insumos,
            "ManoObra": total_mano_obra,
            "TotalGeneral": total_insumos + total_mano_obra,
        }

def crear_cierre_mensual(ini, fin, creado_por, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("INSERT INTO cierres_mensuales (mes_inicio, mes_fin, creado_por, owner) VALUES (%s, %s, %s, %s) RETURNING id",
            (ini, fin, creado_por, owner))
        pid = cur.fetchone()[0]
        conn.commit()
        return pid

def listar_cierres(owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT id, mes_inicio, mes_fin, creado_por, fecha_creacion, total_nomina, total_insumos, total_general FROM cierres_mensuales WHERE owner=%s ORDER BY id DESC", (owner,))
        return cur.fetchall()

# --- EXPORTACIONES (Excel) ---
def get_export_jornadas(owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT id, fecha, trabajador, lote, actividad, dias, horas_extra FROM jornadas WHERE owner=%s ORDER BY fecha DESC", (owner,))
        return cur.fetchall()

def get_export_recolecciones(owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT id, fecha, trabajador, lote, cajuelas, precio_cajuela, total_pagar FROM recolecciones WHERE owner=%s ORDER BY fecha DESC", (owner,))
        return cur.fetchall()

def get_export_insumos(owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT id, fecha, lote, tipo, producto, dosis, cantidad, precio_unitario, costo_total FROM insumos WHERE owner=%s ORDER BY fecha DESC", (owner,))
        return cur.fetchall()


# ==========================================
# 🗺️ MAPAS & GPS
# ==========================================

def update_finca_coords(nombre, lat, lon, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("UPDATE fincas SET latitud=%s, longitud=%s WHERE nombre=%s AND owner=%s", (lat, lon, nombre, owner))
        conn.commit()

def update_finca_polygon(nombre, geojson_str, owner):
    with get_db_cursor() as (cur, conn):
        cur.execute("UPDATE fincas SET poligono_geojson=%s WHERE nombre=%s AND owner=%s", (geojson_str, nombre, owner))
        conn.commit()

def get_fincas_con_coords(owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT nombre, latitud, longitud FROM fincas WHERE owner=%s", (owner,))
        return cur.fetchall()

def get_fincas_full_data(owner):
    with get_db_cursor() as (cur, _):
        cur.execute("SELECT nombre, latitud, longitud, poligono_geojson FROM fincas WHERE owner=%s", (owner,))
        return cur.fetchall()

def get_estado_lote(lote, owner):
    with get_db_cursor() as (cur, _):
        # 1. Chequear Abono Reciente (30 días)
        cur.execute("SELECT COUNT(*) FROM insumos WHERE owner=%s AND lote=%s AND tipo='Abono' AND fecha >= CURRENT_DATE - INTERVAL '30 days'", (owner, lote))
        if cur.fetchone()[0] > 0: return ("green", "✅ Recién Abonado")

        # 2. Chequear Producción baja
        cur.execute("SELECT SUM(cajuelas) FROM recolecciones WHERE owner=%s AND lote=%s", (owner, lote))
        res_prod = cur.fetchone()
        prod_total = float(res_prod[0]) if res_prod and res_prod[0] else 0.0
        
        if prod_total < 50: return ("red", f"⚠️ Baja Producción ({prod_total} caj)")
        return ("blue", "Estable")
