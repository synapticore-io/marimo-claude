# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "duckdb==1.5.1",
#     "marimo",
#     "numpy==2.4.4",
#     "pandas==3.0.2",
# ]
# ///

import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import duckdb
    import numpy

    return duckdb, mo


@app.cell
def _(duckdb, mo):
    con = duckdb.connect()
    con.execute("INSTALL astro FROM community")
    con.execute("LOAD astro")
    mo.md("**DuckDB + Astro Extension geladen**")
    return (con,)


@app.cell
def _(con, mo):
    fns = con.execute("""
        SELECT function_name, description
        FROM duckdb_functions()
        WHERE function_name LIKE 'astro%'
        ORDER BY function_name
    """).df()
    mo.ui.table(fns, label="Astro-Funktionen")
    return


@app.cell
def _(con, mo):
    stars = con.execute("""
        SELECT 'Sirius'     AS name, -1.46 AS magnitude, 101.287 AS ra_deg, -16.716 AS dec_deg UNION ALL
        SELECT 'Canopus',   -0.74,  95.988, -52.696 UNION ALL
        SELECT 'Arcturus',  -0.05, 213.915,  19.182 UNION ALL
        SELECT 'Vega',       0.03, 279.235,  38.783 UNION ALL
        SELECT 'Capella',    0.08,  79.172,  45.998 UNION ALL
        SELECT 'Rigel',      0.13,  78.634,  -8.202 UNION ALL
        SELECT 'Procyon',    0.38, 114.825,   5.225 UNION ALL
        SELECT 'Betelgeuse', 0.42,  88.793,   7.407
    """).df()
    mo.ui.table(stars, label="Hellste Sterne (J2000 Koordinaten)")
    return


@app.cell
def _(con, mo):
    sep = con.execute("""
        WITH s AS (
            SELECT 'Sirius'     AS name, 101.287 AS ra, -16.716 AS dec UNION ALL
            SELECT 'Canopus',    95.988, -52.696 UNION ALL
            SELECT 'Arcturus',  213.915,  19.182 UNION ALL
            SELECT 'Vega',      279.235,  38.783 UNION ALL
            SELECT 'Rigel',      78.634,  -8.202
        )
        SELECT
            a.name AS stern_a,
            b.name AS stern_b,
            ROUND(degrees(astro_angular_separation(
                radians(a.ra), radians(a.dec),
                radians(b.ra), radians(b.dec)
            )), 2) AS abstand_grad
        FROM s a CROSS JOIN s b
        WHERE a.name < b.name
        ORDER BY abstand_grad
    """).df()
    mo.ui.table(sep, label="Winkelabstände zwischen Sternen (Grad)")
    return


if __name__ == "__main__":
    app.run()
