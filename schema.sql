-- Tabelas do sistema (rodam automaticamente quando o app inicia)

CREATE TABLE IF NOT EXISTS cliente (
    id        SERIAL PRIMARY KEY,
    nome      VARCHAR(120) NOT NULL,
    endereco  VARCHAR(255),
    email     VARCHAR(120) UNIQUE
);

CREATE TABLE IF NOT EXISTS produto (
    id         SERIAL PRIMARY KEY,
    nome       VARCHAR(120) NOT NULL,
    valor      NUMERIC(10,2) NOT NULL CHECK (valor >= 0),
    descricao  TEXT,
    foto       VARCHAR(500)          -- URL da imagem
);

CREATE TABLE IF NOT EXISTS venda (
    id          SERIAL PRIMARY KEY,
    cliente_id  INTEGER NOT NULL REFERENCES cliente(id),
    data        TIMESTAMP NOT NULL DEFAULT NOW(),
    pagamento   VARCHAR(30) NOT NULL,
    entrega     VARCHAR(30) NOT NULL
);

-- Tabela intermediária: Venda N <-> N Produto (o "Produtos: Produto[]" do quadro)
CREATE TABLE IF NOT EXISTS venda_produto (
    venda_id        INTEGER NOT NULL REFERENCES venda(id) ON DELETE CASCADE,
    produto_id      INTEGER NOT NULL REFERENCES produto(id),
    quantidade      INTEGER NOT NULL DEFAULT 1 CHECK (quantidade > 0),
    valor_unitario  NUMERIC(10,2) NOT NULL,
    PRIMARY KEY (venda_id, produto_id)
);
