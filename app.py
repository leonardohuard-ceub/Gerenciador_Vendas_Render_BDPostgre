import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave")

# No Render, DATABASE_URL vem do banco. Localmente, use o valor padrão abaixo.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/loja"
)


def conectar():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def criar_tabelas():
    sql = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    with conectar() as conn:
        conn.execute(sql)


criar_tabelas()


# ---------------- INDEX ----------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------- CADASTRO DE CLIENTE ----------------
@app.route("/clientes", methods=["GET", "POST"])
def cad_cliente():
    if request.method == "POST":
        try:
            with conectar() as conn:
                conn.execute(
                    "INSERT INTO cliente (nome, endereco, email) VALUES (%s, %s, %s)",
                    (request.form["nome"], request.form["endereco"],
                     request.form["email"] or None),
                )
            flash("Cliente cadastrado!", "ok")
        except psycopg.errors.UniqueViolation:
            flash("Já existe um cliente com esse e-mail.", "erro")
        return redirect(url_for("cad_cliente"))

    with conectar() as conn:
        clientes = conn.execute("SELECT * FROM cliente ORDER BY nome").fetchall()
    return render_template("cad_cliente.html", clientes=clientes)


# ---------------- CADASTRO DE PRODUTO ----------------
@app.route("/produtos", methods=["GET", "POST"])
def cad_produto():
    if request.method == "POST":
        with conectar() as conn:
            conn.execute(
                "INSERT INTO produto (nome, valor, descricao, foto) VALUES (%s, %s, %s, %s)",
                (request.form["nome"], request.form["valor"].replace(",", "."),
                 request.form["descricao"], request.form["foto"]),
            )
        flash("Produto cadastrado!", "ok")
        return redirect(url_for("cad_produto"))

    with conectar() as conn:
        produtos = conn.execute("SELECT * FROM produto ORDER BY nome").fetchall()
    return render_template("cad_produto.html", produtos=produtos)


# ---------------- VENDA ----------------
@app.route("/vendas", methods=["GET", "POST"])
def venda():
    if request.method == "POST":
        # Cada produto tem um campo "qtd_<id>"; só entram os com quantidade > 0
        itens = {}
        for chave, valor in request.form.items():
            if chave.startswith("qtd_") and valor.strip() and int(valor) > 0:
                itens[int(chave[4:])] = int(valor)

        if not itens:
            flash("Escolha pelo menos um produto.", "erro")
            return redirect(url_for("venda"))

        with conectar() as conn:  # tudo numa transação só
            venda_id = conn.execute(
                "INSERT INTO venda (cliente_id, pagamento, entrega) "
                "VALUES (%s, %s, %s) RETURNING id",
                (request.form["cliente_id"], request.form["pagamento"],
                 request.form["entrega"]),
            ).fetchone()["id"]

            for produto_id, qtd in itens.items():
                conn.execute(
                    "INSERT INTO venda_produto (venda_id, produto_id, quantidade, valor_unitario) "
                    "SELECT %s, id, %s, valor FROM produto WHERE id = %s",
                    (venda_id, qtd, produto_id),
                )
        flash(f"Venda nº {venda_id} registrada!", "ok")
        return redirect(url_for("venda"))

    with conectar() as conn:
        clientes = conn.execute("SELECT id, nome FROM cliente ORDER BY nome").fetchall()
        produtos = conn.execute("SELECT * FROM produto ORDER BY nome").fetchall()
        vendas = conn.execute("""
            SELECT v.id, v.data, v.pagamento, v.entrega, c.nome AS cliente,
                   SUM(vp.quantidade * vp.valor_unitario) AS total
            FROM venda v
            JOIN cliente c ON c.id = v.cliente_id
            JOIN venda_produto vp ON vp.venda_id = v.id
            GROUP BY v.id, c.nome
            ORDER BY v.data DESC
        """).fetchall()
    return render_template("venda.html", clientes=clientes,
                           produtos=produtos, vendas=vendas)


# ---------------- CONSULTA ----------------
@app.route("/consulta")
def consulta():
    with conectar() as conn:
        # Produtos mais vendidos
        produtos = conn.execute("""
            SELECT p.nome, SUM(vp.quantidade) AS qtd_vendida,
                   SUM(vp.quantidade * vp.valor_unitario) AS faturamento
            FROM produto p
            JOIN venda_produto vp ON vp.produto_id = p.id
            GROUP BY p.id, p.nome
            ORDER BY qtd_vendida DESC
        """).fetchall()

        # Clientes que mais compram
        clientes = conn.execute("""
            SELECT c.nome, COUNT(DISTINCT v.id) AS num_compras,
                   SUM(vp.quantidade * vp.valor_unitario) AS total_gasto
            FROM cliente c
            JOIN venda v ON v.cliente_id = c.id
            JOIN venda_produto vp ON vp.venda_id = v.id
            GROUP BY c.id, c.nome
            ORDER BY total_gasto DESC
        """).fetchall()
    return render_template("consulta.html", produtos=produtos, clientes=clientes)


if __name__ == "__main__":
    app.run(debug=True)
