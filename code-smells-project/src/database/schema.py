"""Schema e dados de exemplo (DDL isolada da camada de acesso a dados).

Mudancas em relacao ao schema original:
  - `usuarios.email` ganha `UNIQUE` (fecha o achado de e-mail duplicado);
  - indices em `pedidos.usuario_id` e `itens_pedido.pedido_id`;
  - as senhas do seed sao gravadas com hash (fecha AP-03) -- as credenciais de
    exemplo continuam sendo admin123 / 123456 / senha123.
"""

import logging

logger = logging.getLogger(__name__)

TABELAS = (
    """
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        descricao TEXT,
        preco REAL,
        estoque INTEGER,
        categoria TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        senha TEXT,
        tipo TEXT DEFAULT 'cliente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        status TEXT DEFAULT 'pendente',
        total REAL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        produto_id INTEGER,
        quantidade INTEGER,
        preco_unitario REAL
    )
    """,
)

INDICES = (
    "CREATE INDEX IF NOT EXISTS ix_pedidos_usuario_id ON pedidos (usuario_id)",
    "CREATE INDEX IF NOT EXISTS ix_itens_pedido_pedido_id ON itens_pedido (pedido_id)",
    "CREATE INDEX IF NOT EXISTS ix_produtos_categoria ON produtos (categoria)",
)

PRODUTOS_EXEMPLO = (
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonomico", 89.90, 50, "informatica"),
    ("Teclado Mecanico", "Teclado mecanico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonomica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa codigo", 59.90, 100, "vestuario"),
)

USUARIOS_EXEMPLO = (
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("Joao Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
)


def criar_schema(conexao, gerar_hash_de_senha):
    """Cria tabelas/indices e popula os dados de exemplo se o banco estiver vazio."""
    cursor = conexao.cursor()
    for ddl in TABELAS:
        cursor.execute(ddl)
    for ddl in INDICES:
        cursor.execute(ddl)
    _garantir_email_unico(cursor)
    conexao.commit()

    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria)"
            " VALUES (?, ?, ?, ?, ?)",
            PRODUTOS_EXEMPLO,
        )

    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            [
                (nome, email, gerar_hash_de_senha(senha), tipo)
                for nome, email, senha, tipo in USUARIOS_EXEMPLO
            ],
        )
    conexao.commit()


def _garantir_email_unico(cursor):
    """Aplica a unicidade tambem em bancos criados antes desta refatoracao.

    `CREATE TABLE IF NOT EXISTS` nao altera uma tabela existente; o indice
    unico cobre esse caso. Se o banco legado ja tiver e-mails duplicados a
    criacao falha -- avisamos e seguimos, porque a checagem de duplicidade no
    `UsuarioService` continua valendo.
    """
    try:
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_email ON usuarios (email)"
        )
    except Exception:
        logger.warning(
            "Nao foi possivel criar o indice unico de e-mail: provavelmente existem "
            "registros duplicados no banco. Deduplique 'usuarios.email' manualmente."
        )
