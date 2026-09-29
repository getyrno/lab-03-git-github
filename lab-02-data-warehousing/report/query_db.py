#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Выполнение SQL-запросов к учебной БД через docker exec psql.

Возвращает строки в виде списка списков, чтобы отчет строился на реальных
результатах выполнения, а не на вписанных вручную значениях.
"""
import subprocess

CONTAINER = "video_rental_lab_pg"
DB = "video_rental_lab"
USER = "labuser"


def query(sql, container=CONTAINER, db=DB, user=USER):
    """Возвращает (columns, rows) для первого результата запроса."""
    proc = subprocess.run(
        ["docker", "exec", "-i", container, "psql", "-U", user, "-d", db,
         "-v", "ON_ERROR_STOP=1", "-A", "-F", "\x1f", "-P", "footer=off",
         "--no-align", "-q", "-c", sql],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    lines = [l for l in proc.stdout.splitlines() if l.strip() != ""]
    if not lines:
        return [], []
    cols = lines[0].split("\x1f")
    rows = [l.split("\x1f") for l in lines[1:]]
    return cols, rows


def scalar(sql, **kw):
    _, rows = query(sql, **kw)
    return rows[0][0] if rows else None


if __name__ == "__main__":
    print(query("SELECT rental_number, status FROM video_rental_3nf.rental ORDER BY rental_id"))
