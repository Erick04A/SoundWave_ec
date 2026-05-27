USE master
GO
IF DB_ID('SoundWaveDB') IS NOT NULL
BEGIN
    ALTER DATABASE SoundWaveDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE
    DROP DATABASE SoundWaveDB
END
GO
DECLARE @sys_spid INT
DECLARE @kill_cmd VARCHAR(20)
DECLARE cur_spids CURSOR FOR
    SELECT session_id FROM sys.dm_exec_sessions WHERE login_name IN ('sw_admin', 'sw_app', 'sw_reportes')
OPEN cur_spids
FETCH NEXT FROM cur_spids INTO @sys_spid
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @kill_cmd = 'KILL ' + CAST(@sys_spid AS VARCHAR(10))
    EXEC(@kill_cmd)
    FETCH NEXT FROM cur_spids INTO @sys_spid
END
CLOSE cur_spids
DEALLOCATE cur_spids
GO
IF EXISTS (SELECT * FROM sys.server_principals WHERE name = 'sw_admin') DROP LOGIN sw_admin
GO
IF EXISTS (SELECT * FROM sys.server_principals WHERE name = 'sw_app') DROP LOGIN sw_app
GO
IF EXISTS (SELECT * FROM sys.server_principals WHERE name = 'sw_reportes') DROP LOGIN sw_reportes
GO
CREATE DATABASE SoundWaveDB COLLATE SQL_Latin1_General_CP1_CI_AS
GO
USE SoundWaveDB
GO
CREATE TYPE t_nombre FROM VARCHAR(100)
GO
CREATE TYPE t_email FROM VARCHAR(150)
GO
CREATE TYPE t_url FROM VARCHAR(255)
GO
CREATE TYPE t_plan FROM VARCHAR(20)
GO
CREATE TYPE t_estado FROM VARCHAR(20)
GO
CREATE SCHEMA catalogo
GO
CREATE SCHEMA negocio
GO
CREATE TABLE negocio.ROL (
    id_rol INT IDENTITY(1,1) NOT NULL,
    nombre_rol t_nombre NOT NULL,
    descripcion VARCHAR(255),
    CONSTRAINT PK_ID_ROL PRIMARY KEY (id_rol),
    CONSTRAINT UK_ROL_NOMBRE UNIQUE (nombre_rol)
)
GO
CREATE TABLE negocio.USUARIO (
    id_usuario INT IDENTITY(1,1) NOT NULL,
    id_rol INT NOT NULL,
    nombre_usuario t_nombre NOT NULL,
    email_usuario t_email NOT NULL,
    contrasena VARCHAR(255) NOT NULL,
    telefono VARCHAR(20),
    pais VARCHAR(80),
    fecha_registro DATETIME NOT NULL DEFAULT GETDATE(),
    estado t_estado NOT NULL DEFAULT 'Activo'
                   CONSTRAINT CK_USUARIO_ESTADO CHECK (estado IN ('Activo','Inactivo')),
    CONSTRAINT PK_ID_USUARIO PRIMARY KEY (id_usuario),
    CONSTRAINT UK_USUARIO_EMAIL UNIQUE (email_usuario),
    CONSTRAINT FK_USUARIO_ROL FOREIGN KEY (id_rol) REFERENCES negocio.ROL(id_rol)
)
GO
CREATE TABLE catalogo.GENERO (
    id_genero INT IDENTITY(1,1) NOT NULL,
    nombre_genero t_nombre NOT NULL,
    descripcion VARCHAR(255),
    CONSTRAINT PK_ID_GENERO PRIMARY KEY (id_genero),
    CONSTRAINT UK_GENERO_NOMBRE UNIQUE (nombre_genero)
)
GO
CREATE TABLE catalogo.ARTISTA (
    id_artista INT IDENTITY(1,1) NOT NULL,
    id_usuario INT NOT NULL,
    nombre_artistico t_nombre NOT NULL,
    biografia VARCHAR(MAX) NOT NULL DEFAULT 'Biografia no disponible',
    pais VARCHAR(80),
    fecha_debut DATE,
    imagen_perfil t_url DEFAULT 'img/default_perfil.png',
    CONSTRAINT PK_ID_ARTISTA PRIMARY KEY (id_artista),
    CONSTRAINT UK_ARTISTA_USUARIO UNIQUE (id_usuario),
    CONSTRAINT FK_ARTISTA_USUARIO FOREIGN KEY (id_usuario) REFERENCES negocio.USUARIO(id_usuario)
)
GO
CREATE TABLE catalogo.ALBUM (
    id_album INT IDENTITY(1,1) NOT NULL,
    id_artista INT NOT NULL,
    titulo_album VARCHAR(150) NOT NULL,
    fecha_lanzamiento DATE,
    portada t_url,
    descripcion VARCHAR(MAX),
    CONSTRAINT PK_ID_ALBUM PRIMARY KEY (id_album),
    CONSTRAINT FK_ALBUM_ARTISTA FOREIGN KEY (id_artista) REFERENCES catalogo.ARTISTA(id_artista)
)
GO
CREATE TABLE catalogo.CANCION (
    id_cancion INT IDENTITY(1,1) NOT NULL,
    id_album INT NOT NULL,
    id_artista INT NOT NULL,
    titulo_cancion VARCHAR(150) NOT NULL,
    duracion_seg INT NOT NULL
                       CONSTRAINT CK_CANCION_DURACION CHECK (duracion_seg > 0),
    url_audio t_url,
    num_reproducciones BIGINT NOT NULL DEFAULT 0,
    fecha_publicacion DATE,
    estado t_estado NOT NULL DEFAULT 'Activo'
                       CONSTRAINT CK_CANCION_ESTADO CHECK (estado IN ('Activo','Inactivo')),
    CONSTRAINT PK_ID_CANCION PRIMARY KEY (id_cancion),
    CONSTRAINT FK_CANCION_ALBUM FOREIGN KEY (id_album) REFERENCES catalogo.ALBUM(id_album),
    CONSTRAINT FK_CANCION_ARTISTA FOREIGN KEY (id_artista) REFERENCES catalogo.ARTISTA(id_artista)
)
GO
CREATE TABLE catalogo.CANCION_GENERO (
    id_cancion INT NOT NULL,
    id_genero INT NOT NULL,
    CONSTRAINT PK_CANCION_GENERO PRIMARY KEY (id_cancion, id_genero),
    CONSTRAINT FK_CG_CANCION FOREIGN KEY (id_cancion) REFERENCES catalogo.CANCION(id_cancion),
    CONSTRAINT FK_CG_GENERO FOREIGN KEY (id_genero) REFERENCES catalogo.GENERO(id_genero)
)
GO
CREATE TABLE negocio.PLAYLIST (
    id_playlist INT IDENTITY(1,1) NOT NULL,
    id_usuario INT NOT NULL,
    nombre_playlist VARCHAR(150) NOT NULL,
    descripcion VARCHAR(MAX),
    es_publica BIT NOT NULL DEFAULT 1,
    fecha_creacion DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT PK_ID_PLAYLIST PRIMARY KEY (id_playlist),
    CONSTRAINT FK_PLAYLIST_USUARIO FOREIGN KEY (id_usuario) REFERENCES negocio.USUARIO(id_usuario)
)
GO
CREATE TABLE negocio.PLAYLIST_CANCION (
    id_playlist INT NOT NULL,
    id_cancion INT NOT NULL,
    orden INT,
    fecha_agregado DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT PK_PLAYLIST_CANCION PRIMARY KEY (id_playlist, id_cancion),
    CONSTRAINT FK_PC_PLAYLIST FOREIGN KEY (id_playlist) REFERENCES negocio.PLAYLIST(id_playlist),
    CONSTRAINT FK_PC_CANCION FOREIGN KEY (id_cancion) REFERENCES catalogo.CANCION(id_cancion)
)
GO
CREATE TABLE negocio.ALBUM_GUARDADO (
    id_usuario INT NOT NULL,
    id_album INT NOT NULL,
    fecha_guardado DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT PK_ALBUM_GUARDADO PRIMARY KEY (id_usuario, id_album),
    CONSTRAINT FK_AG_USUARIO FOREIGN KEY (id_usuario) REFERENCES negocio.USUARIO(id_usuario),
    CONSTRAINT FK_AG_ALBUM FOREIGN KEY (id_album) REFERENCES catalogo.ALBUM(id_album)
)
GO
CREATE TABLE negocio.HISTORIAL_REPRODUCCION (
    id_historial INT IDENTITY(1,1) NOT NULL,
    id_usuario INT NOT NULL,
    id_cancion INT NOT NULL,
    fecha_hora DATETIME NOT NULL DEFAULT GETDATE(),
    duracion_escuchada INT,
    CONSTRAINT PK_ID_HISTORIAL PRIMARY KEY (id_historial),
    CONSTRAINT FK_HR_USUARIO FOREIGN KEY (id_usuario) REFERENCES negocio.USUARIO(id_usuario),
    CONSTRAINT FK_HR_CANCION FOREIGN KEY (id_cancion) REFERENCES catalogo.CANCION(id_cancion)
)
GO
CREATE TABLE negocio.SUSCRIPCION (
    id_suscripcion INT IDENTITY(1,1) NOT NULL,
    id_usuario INT NOT NULL,
    tipo_plan t_plan NOT NULL
                   CONSTRAINT CK_SUSC_PLAN CHECK (tipo_plan IN ('Gratuito','Premium')),
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE,
    estado t_estado NOT NULL DEFAULT 'Activa'
                   CONSTRAINT CK_SUSC_ESTADO CHECK (estado IN ('Activa','Vencida','Cancelada')),
    CONSTRAINT PK_ID_SUSCRIPCION PRIMARY KEY (id_suscripcion),
    CONSTRAINT FK_SUSC_USUARIO FOREIGN KEY (id_usuario) REFERENCES negocio.USUARIO(id_usuario)
)
GO
CREATE TABLE negocio.PAGO (
    id_pago INT IDENTITY(1,1) NOT NULL,
    id_suscripcion INT NOT NULL,
    fecha_pago DATETIME NOT NULL DEFAULT GETDATE(),
    monto DECIMAL(10,2) NOT NULL
                   CONSTRAINT CK_PAGO_MONTO CHECK (monto > 0),
    metodo_pago VARCHAR(50),
    estado_pago t_estado NOT NULL DEFAULT 'Completado'
                   CONSTRAINT CK_PAGO_ESTADO CHECK (estado_pago IN ('Completado','Fallido','Pendiente')),
    CONSTRAINT PK_ID_PAGO PRIMARY KEY (id_pago),
    CONSTRAINT FK_PAGO_SUSCRIPCION FOREIGN KEY (id_suscripcion) REFERENCES negocio.SUSCRIPCION(id_suscripcion)
)
GO
CREATE TABLE negocio.REGALIAS (
    id_regalia INT IDENTITY(1,1) NOT NULL,
    id_artista INT NOT NULL,
    periodo VARCHAR(7) NOT NULL,
    total_reprod BIGINT NOT NULL DEFAULT 0,
    monto_calculado DECIMAL(12,4),
    fecha_calculo DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT PK_ID_REGALIA PRIMARY KEY (id_regalia),
    CONSTRAINT UK_REG_ART_PER UNIQUE (id_artista, periodo),
    CONSTRAINT FK_REG_ARTISTA FOREIGN KEY (id_artista) REFERENCES catalogo.ARTISTA(id_artista)
)
GO
CREATE TABLE negocio.SEGUIMIENTO_ARTISTA (
    id_usuario INT NOT NULL,
    id_artista INT NOT NULL,
    fecha_seguimiento DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT PK_SEGUIMIENTO PRIMARY KEY (id_usuario, id_artista),
    CONSTRAINT FK_SA_USUARIO FOREIGN KEY (id_usuario) REFERENCES negocio.USUARIO(id_usuario),
    CONSTRAINT FK_SA_ARTISTA FOREIGN KEY (id_artista) REFERENCES catalogo.ARTISTA(id_artista)
)
GO
CREATE TABLE negocio.LIKES (
    id_usuario INT NOT NULL,
    id_cancion INT NOT NULL,
    fecha_like DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT PK_LIKES PRIMARY KEY (id_usuario, id_cancion),
    CONSTRAINT FK_LIKES_USUARIO FOREIGN KEY (id_usuario) REFERENCES negocio.USUARIO(id_usuario),
    CONSTRAINT FK_LIKES_CANCION FOREIGN KEY (id_cancion) REFERENCES catalogo.CANCION(id_cancion)
)
GO
CREATE TABLE negocio.NOTIFICACION (
    id_notificacion INT IDENTITY(1,1) NOT NULL,
    id_usuario INT NOT NULL,
    tipo VARCHAR(50),
    mensaje VARCHAR(MAX),
    fecha_envio DATETIME NOT NULL DEFAULT GETDATE(),
    leida BIT NOT NULL DEFAULT 0,
    CONSTRAINT PK_ID_NOTIFICACION PRIMARY KEY (id_notificacion),
    CONSTRAINT FK_NOTIF_USUARIO FOREIGN KEY (id_usuario) REFERENCES negocio.USUARIO(id_usuario)
)
GO
CREATE NONCLUSTERED INDEX IDX_HISTORIAL_USUARIO_FECHA
    ON negocio.HISTORIAL_REPRODUCCION (id_usuario, fecha_hora DESC)
GO
CREATE NONCLUSTERED INDEX IDX_CANCION_ARTISTA_REPROD
    ON catalogo.CANCION (id_artista, num_reproducciones DESC)
GO
CREATE NONCLUSTERED INDEX IDX_SUSCRIPCION_USUARIO_ESTADO
    ON negocio.SUSCRIPCION (id_usuario, estado)
GO
CREATE NONCLUSTERED INDEX IDX_REGALIAS_ARTISTA_PERIODO
    ON negocio.REGALIAS (id_artista, periodo)
GO
CREATE NONCLUSTERED INDEX IDX_LIKES_USUARIO
    ON negocio.LIKES (id_usuario)
GO
USE master
GO
CREATE LOGIN sw_admin WITH PASSWORD = 'SWAdmin#2026!'
GO
CREATE LOGIN sw_app WITH PASSWORD = 'SWApp#2026!'
GO
CREATE LOGIN sw_reportes WITH PASSWORD = 'SWReport#2026!'
GO
USE SoundWaveDB
GO
CREATE USER sw_admin FOR LOGIN sw_admin
GO
CREATE USER sw_app FOR LOGIN sw_app
GO
CREATE USER sw_reportes FOR LOGIN sw_reportes
GO
ALTER ROLE db_owner ADD MEMBER sw_admin
GO
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON SCHEMA::negocio TO sw_app
GO
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::catalogo TO sw_app
GO
GRANT SELECT ON SCHEMA::catalogo TO sw_reportes
GO
GRANT SELECT ON SCHEMA::negocio TO sw_reportes
GO
SET IDENTITY_INSERT negocio.ROL ON
INSERT INTO negocio.ROL (id_rol, nombre_rol, descripcion) VALUES
    (1, 'Administrador', 'Acceso total al sistema'),
    (2, 'Artista',       'Publica contenido y consulta regalias'),
    (3, 'Oyente',        'Reproduce musica y crea playlists'),
    (4, 'Premium',       'Oyente con beneficios adicionales')
SET IDENTITY_INSERT negocio.ROL OFF
GO
SET IDENTITY_INSERT negocio.USUARIO ON
INSERT INTO negocio.USUARIO (id_usuario, id_rol, nombre_usuario, email_usuario, contrasena, estado) VALUES
    (1,  1, 'Admin Sistema',          'admin@soundwave.ec',         'hash_admin123',   'Activo'),
    (2,  2, 'Benito Martinez',        'badbunny@soundwave.ec',      'hash_bbunny456',  'Activo'),
    (3,  2, 'Carolina Giraldo',       'karolg@soundwave.ec',        'hash_karolg789',  'Activo'),
    (4,  2, 'Shakira Mebarak',        'shakira@soundwave.ec',       'hash_shak000',    'Activo'),
    (5,  2, 'Abel Tesfaye',           'weeknd@soundwave.ec',        'hash_weeknd111',  'Activo'),
    (6,  2, 'Amaia Montero',          'laoreja@soundwave.ec',       'hash_laoreja',    'Activo'),
    (7,  2, N'José José',              N'josejose@soundwave.ec',      N'hash_josejose77', N'Activo'),
    (8,  2, 'Cari Cari',              'caricari@soundwave.ec',      'hash_caricari',   'Activo'),
    (9,  2, 'Ed Sheeran',             'edsheeran@soundwave.ec',     'hash_edsheeran',  'Activo'),
    (10, 2, 'Warhaus',                'warehouse@soundwave.ec',     'hash_warehouse',  'Activo'),
    (11, 2, 'Gismo Varillas',         'gismo@soundwave.ec',         'hash_gismo',      'Activo'),
    (12, 3, 'Maria Lopez',            'mlopez@soundwave.ec',        'hash_mlopez01',   'Activo'),
    (13, 3, 'Carlos Vega',            'cvega@soundwave.ec',         'hash_cvega02',    'Activo'),
    (14, 3, 'Ana Torres',             'atorres@soundwave.ec',       'hash_atorres03',  'Activo'),
    (15, 4, 'Luis Paredes',           'lparedes@soundwave.ec',      'hash_lpar04',     'Activo'),
    (16, 3, 'Sofia Ruiz',             'sruiz@soundwave.ec',         'hash_sruiz05',    'Activo'),
    (17, 4, 'Diego Mora',             'dmora@soundwave.ec',         'hash_dmora06',    'Activo'),
    (18, 3, 'Paula Jimenez',          'pjimenez@soundwave.ec',      'hash_pjim07',     'Activo'),
    (19, 4, 'Andres Castro',          'acastro@soundwave.ec',       'hash_acast08',    'Activo'),
    (20, 3, 'Valeria Rios',           'vrios@soundwave.ec',         'hash_vrios09',    'Activo'),
    (21, 3, 'Mateo Herrera',          'mherrera@soundwave.ec',      'hash_mher10',     'Activo'),
    (22, 3, 'Camila Flores',          'cflores@soundwave.ec',       'hash_cflor11',    'Activo')
SET IDENTITY_INSERT negocio.USUARIO OFF
GO
SET IDENTITY_INSERT catalogo.GENERO ON
INSERT INTO catalogo.GENERO (id_genero, nombre_genero, descripcion) VALUES
    (1, 'Reggaeton',    'Ritmo urbano latinoamericano'),
    (2, 'Pop Latino',   'Pop en espanol con influencias latinas'),
    (3, 'R&B',          'Rhythm and Blues contemporaneo'),
    (4, 'Pop',          'Musica popular de alcance masivo'),
    (5, 'Trap Latino',  'Trap con lirica en espanol'),
    (6, 'Hip-Hop',      'Cultura urbana norteamericana'),
    (7, 'Flamenco Pop', 'Fusion de flamenco y pop moderno'),
    (8, 'Electropop',   'Electronica y pop combinados')
SET IDENTITY_INSERT catalogo.GENERO OFF
GO
SET IDENTITY_INSERT catalogo.ARTISTA ON
INSERT INTO catalogo.ARTISTA (id_artista, id_usuario, nombre_artistico, pais, fecha_debut) VALUES
    (1,  2,  'Bad Bunny',              'Puerto Rico', '2017-03-10'),
    (2,  3,  'Karol G',                'Colombia',    '2010-06-14'),
    (3,  4,  'Shakira',                'Colombia',    '1991-11-19'),
    (4,  5,  'The Weeknd',             'Canada',      '2010-10-21'),
    (5,  6,  'La Oreja de Van Gogh',   'Espana',      '1996-01-01'),
    (6,  7,  N'José José',              N'Mexico',      N'1963-03-12'),
    (7,  8,  'Cari Cari',              'Austria',     '2017-06-01'),
    (8,  9,  'Ed Sheeran',             'UK',          '2011-06-12'),
    (9,  10, 'Warhaus',                'USA',         '2020-01-01'),
    (10, 11, 'Gismo Varillas',         'Espana',      '2017-01-01')
SET IDENTITY_INSERT catalogo.ARTISTA OFF
GO
SET IDENTITY_INSERT catalogo.ALBUM ON
INSERT INTO catalogo.ALBUM (id_album, id_artista, titulo_album, fecha_lanzamiento) VALUES
    (1,  1,  'Un Verano Sin Ti',        '2022-05-06'),
    (2,  2,  'Manana Sera Bonito',      '2023-02-24'),
    (3,  3,  'Las Mujeres Ya No Lloran','2024-03-22'),
    (4,  4,  'Dawn FM',                 '2022-01-07'),
    (5,  5,  'El Viaje de Copperpot',   '2000-09-11'),
    (6,  6,  'Secretos',                '1983-05-30'),
    (7,  7,  'Anaana',                  '2018-05-18'),
    (8,  8,  'Divide',                  '2017-03-03'),
    (9,  9,  'Warhaus',                 '2022-11-04'),
    (10, 10, 'El Camino back to Sun',   '2017-05-01')
SET IDENTITY_INSERT catalogo.ALBUM OFF
GO
SET IDENTITY_INSERT catalogo.CANCION ON
INSERT INTO catalogo.CANCION (id_cancion, id_album, id_artista, titulo_cancion, duracion_seg, url_audio, fecha_publicacion) VALUES
    (1,  1,  1,  'Titi Me Pregunto',    188, '/audio/001.mp3', '2022-05-06'),
    (2,  2,  2,  'TQG',                 200, '/audio/004.mp3', '2023-02-24'),
    (3,  4,  4,  'Blinding Lights',     200, '/audio/017.mp3', '2019-11-29'),
    (4,  5,  5,  'Rosas',               236, '/audio/rosas.mp3', '2000-09-11'),
    (5,  5,  5,  'La Playa',            247, '/audio/la_playa.mp3', '2000-09-11'),
    (6,  5,  5,  '20 de Enero',         220, '/audio/20_de_enero.mp3', '2000-09-11'),
    (7,  6,  6,  'El Triste',           250, '/audio/el_triste.mp3', '1970-03-01'),
    (8,  6,  6,  'Almohada',            210, '/audio/almohada.mp3', '1978-01-01'),
    (9,  6,  6,  'Gavilán o Paloma',    260, '/audio/gavilan_o_paloma.mp3', '1977-01-01'),
    (10, 6,  6,  'La Nave del Olvido',  230, '/audio/la_nave_del_olvido.mp3', '1970-01-01'),
    (11, 7,  7,  'Summer Sun',          210, '/audio/summer_sun.mp3', '2018-05-18'),
    (12, 7,  7,  'Mazuka',              200, '/audio/mazuka.mp3', '2018-05-18'),
    (13, 8,  8,  'Shape of You',        233, '/audio/shape_of_you.mp3', '2017-03-03'),
    (14, 9,  9,  'Loves a Stranger',    215, '/audio/loves_a_stranger.mp3', '2022-11-04'),
    (15, 10, 10, 'Follow the Sun',      220, '/audio/follow_the_sun.mp3', '2017-05-01')
SET IDENTITY_INSERT catalogo.CANCION OFF
GO
INSERT INTO catalogo.CANCION_GENERO (id_cancion, id_genero) VALUES
    (1,1),(1,5),(2,1),(2,2),(3,3),(3,4),(4,2),(5,2),(6,2),(7,2),
    (8,2),(9,2),(10,2),(11,4),(12,4),(13,4),(14,4),(15,2)
GO
SET IDENTITY_INSERT negocio.PLAYLIST ON
INSERT INTO negocio.PLAYLIST (id_playlist, id_usuario, nombre_playlist, descripcion, es_publica) VALUES
    (1,  12, 'Mis Favoritas',   'Canciones que me encantan',  1),
    (2,  13, 'Para Trabajar',   'Musica de concentracion',    0),
    (3,  14, 'Reggaeton Mix',   'Lo mejor del reggaeton',     1),
    (4,  15, 'Chill Vibes',     'Para relajarse',             1),
    (5,  16, 'Workout',         'Energia al maximo',          0),
    (6,  17, 'Late Night',      'Para la noche',              1),
    (7,  18, 'Pop Hits',        'Exitos del pop',             1),
    (8,  19, 'Romanticas',      'Baladas y romanticas',       0),
    (9,  20, 'Descubrimientos', 'Canciones nuevas',           1),
    (10, 12, 'Latin Vibes',     'Lo mejor de latinoamerica',  1)
SET IDENTITY_INSERT negocio.PLAYLIST OFF
GO
INSERT INTO negocio.PLAYLIST_CANCION (id_playlist, id_cancion, orden) VALUES
    (1,1,1),(1,2,2),(1,3,3),(1,4,4),(1,7,5),
    (2,13,1),(2,14,2),(2,15,3),(2,3,4),
    (3,1,1),(3,2,2),(3,4,3),(3,5,4),(3,6,5),
    (4,7,1),(4,8,2),(4,9,3),(4,10,4),
    (5,1,1),(5,2,2),(5,11,3),(5,12,4),(5,13,5),
    (6,3,1),(6,13,2),(6,14,3),(6,15,4),
    (7,4,1),(7,5,2),(7,11,3),(7,12,4),(7,13,5),
    (8,7,1),(8,8,2),(8,9,3),(8,10,4),
    (9,11,1),(9,12,2),(9,13,3),(9,14,4),(9,15,5),
    (10,1,1),(10,2,2),(10,4,3),(10,5,4),(10,7,5),(10,8,6),(10,15,7)
GO
SET IDENTITY_INSERT negocio.SUSCRIPCION ON
INSERT INTO negocio.SUSCRIPCION (id_suscripcion, id_usuario, tipo_plan, fecha_inicio, fecha_fin, estado) VALUES
    (1, 12, 'Gratuito', '2026-01-01', '2026-12-31', 'Activa'),
    (2, 15, 'Premium', '2026-02-01', '2026-04-30', 'Activa'),
    (3, 16, 'Premium', '2025-12-01', '2026-02-28', 'Vencida'),
    (4, 17, 'Premium', '2026-03-01', '2026-05-31', 'Activa'),
    (5, 19, 'Premium', '2026-01-15', '2026-07-15', 'Activa'),
    (6, 20, 'Premium', '2025-10-01', '2026-01-01', 'Vencida'),
    (7, 21, 'Premium', '2026-01-01', '2026-06-30', 'Activa'),
    (8, 22, 'Premium', '2026-04-01', '2026-04-30', 'Cancelada')
SET IDENTITY_INSERT negocio.SUSCRIPCION OFF
GO
SET IDENTITY_INSERT negocio.PAGO ON
INSERT INTO negocio.PAGO (id_pago, id_suscripcion, fecha_pago, monto, metodo_pago, estado_pago) VALUES
    (1,  1, '2026-01-01', 9.99, 'Tarjeta Credito', 'Completado'),
    (2,  2, '2026-02-01', 9.99, 'PayPal',           'Completado'),
    (3,  3, '2025-12-01', 9.99, 'Tarjeta Debito',   'Completado'),
    (4,  3, '2026-02-01', 9.99, 'Tarjeta Debito',   'Fallido'),
    (5,  4, '2026-03-01', 9.99, 'Transferencia',    'Completado'),
    (6,  5, '2026-01-15', 9.99, 'PayPal',           'Completado'),
    (7,  6, '2025-10-01', 9.99, 'Tarjeta Credito',  'Completado'),
    (8,  7, '2026-01-01', 9.99, 'Tarjeta Credito',  'Completado'),
    (9,  7, '2026-02-01', 9.99, 'Tarjeta Credito',  'Completado'),
    (10, 7, '2026-03-01', 9.99, 'Tarjeta Credito',  'Completado'),
    (11, 8, '2026-04-01', 9.99, 'PayPal',           'Completado'),
    (12, 2, '2026-03-01', 9.99, 'PayPal',           'Completado')
SET IDENTITY_INSERT negocio.PAGO OFF
GO
SET IDENTITY_INSERT negocio.HISTORIAL_REPRODUCCION ON
INSERT INTO negocio.HISTORIAL_REPRODUCCION (id_historial, id_usuario, id_cancion, fecha_hora, duracion_escuchada) VALUES
    (1,  12, 1, '2026-01-05 08:14:00', 188),
    (2,  13, 2, '2026-01-06 19:32:00', 200),
    (3,  12, 3, '2026-01-08 11:45:00', 200),
    (4,  14, 4, '2026-01-10 21:03:00', 236),
    (5,  13, 5, '2026-01-12 07:58:00', 247),
    (6,  12, 6, '2026-01-14 16:20:00', 220),
    (7,  14, 7, '2026-01-16 22:11:00', 250),
    (8,  13, 8, '2026-01-18 09:05:00', 210),
    (9,  12, 9, '2026-01-20 14:30:00', 260),
    (10, 14, 10, '2026-01-22 20:47:00', 230),
    (11, 15, 11, '2026-01-24 08:00:00', 210),
    (12, 16, 12, '2026-01-26 10:15:00', 200),
    (13, 17, 13, '2026-01-28 18:30:00', 233),
    (14, 18, 14, '2026-01-30 07:45:00', 215),
    (15, 19, 15, '2026-02-01 21:00:00', 220),
    (16, 12, 1, '2026-02-03 15:30:00', 188),
    (17, 13, 2, '2026-02-05 11:00:00', 200),
    (18, 14, 3, '2026-02-07 23:15:00', 200),
    (19, 15, 4, '2026-02-09 09:30:00', 236),
    (20, 16, 5, '2026-02-11 16:45:00', 247),
    (21, 17, 6, '2026-02-13 20:00:00', 220),
    (22, 18, 7, '2026-02-15 12:30:00', 250),
    (23, 19, 8, '2026-02-17 08:15:00', 210),
    (24, 20, 9, '2026-02-19 17:00:00', 260),
    (25, 21, 10, '2026-02-21 22:30:00', 230),
    (26, 12, 11, '2026-02-23 10:00:00', 210),
    (27, 13, 12, '2026-02-25 14:15:00', 200),
    (28, 14, 13, '2026-02-27 19:30:00', 233),
    (29, 15, 14, '2026-03-01 08:45:00', 215),
    (30, 16, 15, '2026-03-03 13:00:00', 220),
    (31, 17, 1, '2026-03-05 21:15:00', 188),
    (32, 18, 2, '2026-03-07 09:30:00', 200),
    (33, 19, 3, '2026-03-09 17:45:00', 200),
    (34, 20, 4, '2026-03-11 11:00:00', 236),
    (35, 21, 5, '2026-03-13 20:15:00', 247),
    (36, 22, 6, '2026-03-15 07:30:00', 220),
    (37, 12, 7, '2026-03-17 15:45:00', 250),
    (38, 13, 8, '2026-03-19 10:00:00', 210),
    (39, 14, 9, '2026-03-21 23:15:00', 260),
    (40, 15, 10, '2026-03-23 09:30:00', 230),
    (41, 16, 11, '2026-03-25 16:45:00', 210),
    (42, 17, 12, '2026-03-27 20:00:00', 200),
    (43, 18, 13, '2026-03-29 12:15:00', 233),
    (44, 19, 14, '2026-03-31 08:30:00', 215),
    (45, 20, 15, '2026-04-01 17:45:00', 220),
    (46, 21, 1, '2026-04-03 11:00:00', 188),
    (47, 22, 2, '2026-04-05 20:15:00', 200),
    (48, 12, 3, '2026-04-07 09:30:00', 200),
    (49, 13, 4, '2026-04-09 16:45:00', 236),
    (50, 14, 5, '2026-04-11 21:00:00', 247),
    (51, 12, 6, '2026-01-07 10:00:00', 220),
    (52, 13, 7, '2026-01-09 14:00:00', 250),
    (53, 14, 8, '2026-01-11 18:00:00', 210),
    (54, 15, 9, '2026-01-13 22:00:00', 260),
    (55, 16, 10, '2026-01-15 08:00:00', 230),
    (56, 17, 11, '2026-01-17 12:00:00', 210),
    (57, 18, 12, '2026-01-19 16:00:00', 200),
    (58, 19, 13, '2026-01-21 20:00:00', 233),
    (59, 20, 14, '2026-01-23 09:00:00', 215),
    (60, 21, 15, '2026-01-25 13:00:00', 220)
SET IDENTITY_INSERT negocio.HISTORIAL_REPRODUCCION OFF
GO
UPDATE catalogo.CANCION
SET num_reproducciones =
    (SELECT COUNT(*) FROM negocio.HISTORIAL_REPRODUCCION WHERE id_cancion = catalogo.CANCION.id_cancion)
GO
INSERT INTO negocio.SEGUIMIENTO_ARTISTA (id_usuario, id_artista) VALUES
    (12,1),(12,2),(12,4),(13,1),(13,3),(13,8),(14,2),(14,5),
    (15,1),(15,4),(16,2),(16,6),(17,3),(18,1),(18,7),(19,4),(20,10)
GO
INSERT INTO negocio.LIKES (id_usuario, id_cancion) VALUES
    (12,1),(12,4),(12,6),(12,8),(13,2),(13,5),(13,9),(14,1),(14,3),
    (14,7),(14,10),(15,1),(15,4),(16,2),(16,6),(17,3),(17,8),(18,5),
    (18,9),(19,1),(19,7),(20,4),(20,10),(21,2),(21,6),(22,1),(22,15),
    (12,11),(13,12),(14,13),(15,14),(16,15),(17,10),(18,15),(19,8),(20,6)
GO
INSERT INTO negocio.ALBUM_GUARDADO (id_usuario, id_album) VALUES
    (12,1),(12,3),(12,5),(13,2),(13,4),(13,6),(14,1),(14,7),
    (15,2),(15,8),(16,1),(16,4),(17,3),(17,5),(18,2),(18,6),(19,9),(20,10)
GO
SET IDENTITY_INSERT negocio.NOTIFICACION ON
INSERT INTO negocio.NOTIFICACION (id_notificacion, id_usuario, tipo, mensaje, leida) VALUES
    (1,  12, 'Bienvenida',        'Bienvenido a SoundWave. Disfruta la musica.',                        0),
    (2,  13, 'Suscripcion',       'Tu suscripcion Premium esta activa hasta el 31/12/2026.',             0),
    (3,  12, 'Nuevo Album',       'Bad Bunny lanzo el album Nadie Sabe Lo Que Va a Pasar Manana.',      0),
    (4,  14, 'Bienvenida',        'Bienvenido a SoundWave. Disfruta la musica.',                        1),
    (5,  15, 'Suscripcion',       'Tu suscripcion Premium esta activa hasta el 30/04/2026.',             0),
    (6,  16, 'Pago Fallido',      'No pudimos renovar tu suscripcion. Por favor actualiza tu metodo.',  0),
    (7,  17, 'Suscripcion',       'Tu suscripcion Premium esta activa hasta el 31/05/2026.',             0),
    (8,  12, 'Nuevo Seguimiento', 'Ahora sigues a Bad Bunny. Seras el primero en ver sus novedades.',   1),
    (9,  12, 'Nuevo Seguimiento', 'Ahora sigues a Karol G. Seras el primero en ver sus novedades.',     1),
    (10, 13, 'Nuevo Seguimiento', 'Ahora sigues a Bad Bunny. Seras el primero en ver sus novedades.',   0),
    (11, 19, 'Suscripcion',       'Tu suscripcion Premium esta activa hasta el 15/07/2026.',             0),
    (12, 21, 'Suscripcion',       'Tu suscripcion Premium esta activa hasta el 30/06/2026.',             0),
    (13, 16, 'Bienvenida',        'Bienvenido a SoundWave. Disfruta la musica.',                        1),
    (14, 20, 'Vencimiento',       'Tu suscripcion Premium ha vencido. Renovala para seguir disfrutando.',0),
    (15, 18, 'Nuevo Album',       'Shakira lanzo Las Mujeres Ya No Lloran.',                            0),
    (16, 17, 'Pago Fallido',      'Pago de suscripcion fallido. Verifica tu metodo de pago.',           1),
    (17, 14, 'Nuevo Seguimiento', 'Ahora sigues a Karol G. Seras el primero en ver sus novedades.',     0),
    (18, 22, 'Bienvenida',        'Bienvenido a SoundWave. Disfruta la musica.',                        0),
    (19, 15, 'Nuevo Seguimiento', 'Ahora sigues a Bad Bunny. Seras el primero en ver sus novedades.',   0),
    (20, 20, 'Bienvenida',        'Bienvenido a SoundWave. Disfruta la musica.',                        1),
    (21, 13, 'Nuevo Album',       'The Weeknd lanzo Dawn FM.',                                          0),
    (22, 16, 'Vencimiento',       'Tu suscripcion ha vencido. Activa un nuevo plan.',                   0),
    (23, 19, 'Nuevo Album',       'La Oreja de Van Gogh lanzo El Viaje de Copperpot.',                  0),
    (24, 21, 'Nuevo Album',       'Bad Bunny lanzo Un Verano Sin Ti.',                                  1)
SET IDENTITY_INSERT negocio.NOTIFICACION OFF
GO
CREATE OR ALTER PROCEDURE negocio.sp_RegistrarReproduccion
    @id_usuario INT,
    @id_cancion INT,
    @duracion   INT
AS BEGIN
    SET NOCOUNT ON
    BEGIN TRY
        BEGIN TRAN
            INSERT INTO negocio.HISTORIAL_REPRODUCCION (id_usuario, id_cancion, duracion_escuchada)
            VALUES (@id_usuario, @id_cancion, @duracion)
            UPDATE catalogo.CANCION
            SET num_reproducciones = num_reproducciones + 1
            WHERE id_cancion = @id_cancion
        COMMIT
        RETURN 0
    END TRY
    BEGIN CATCH
        ROLLBACK
        ;THROW
    END CATCH
END
GO
CREATE OR ALTER PROCEDURE negocio.sp_CalcularRegalias
    @id_artista INT,
    @periodo    VARCHAR(7)
AS BEGIN
    SET NOCOUNT ON
    IF EXISTS (SELECT 1 FROM negocio.REGALIAS WHERE id_artista = @id_artista AND periodo = @periodo)
    BEGIN
        PRINT 'ADVERTENCIA: Ya existe calculo para ' + @periodo
        RETURN 1
    END
    DECLARE @tarifa       DECIMAL(12,6) = 0.004
    DECLARE @total_reprod BIGINT
    DECLARE @monto        DECIMAL(12,4)
    SELECT @total_reprod = COUNT(*)
    FROM negocio.HISTORIAL_REPRODUCCION H
    INNER JOIN catalogo.CANCION C ON H.id_cancion = C.id_cancion
    WHERE C.id_artista = @id_artista
      AND FORMAT(H.fecha_hora, 'yyyy-MM') = @periodo
    SET @monto = @total_reprod * @tarifa
    INSERT INTO negocio.REGALIAS (id_artista, periodo, total_reprod, monto_calculado)
    VALUES (@id_artista, @periodo, @total_reprod, @monto)
    RETURN 0
END
GO
CREATE OR ALTER PROCEDURE negocio.sp_ProcesarRenovacion
    @id_suscripcion INT,
    @estado_pago    VARCHAR(20),
    @metodo         VARCHAR(50) = 'Tarjeta Credito'
AS BEGIN
    SET NOCOUNT ON
    DECLARE @id_usuario INT
    DECLARE @monto      DECIMAL(10,2) = 9.99
    DECLARE @msg        VARCHAR(500)
    DECLARE @tipo_notif VARCHAR(50)
    SET @id_usuario = (SELECT TOP 1 id_usuario FROM negocio.SUSCRIPCION WHERE id_suscripcion = @id_suscripcion)
    BEGIN TRY
        BEGIN TRAN
            INSERT INTO negocio.PAGO (id_suscripcion, monto, metodo_pago, estado_pago)
            VALUES (@id_suscripcion, @monto, @metodo, @estado_pago)
            IF @estado_pago = 'Completado'
            BEGIN
                UPDATE negocio.SUSCRIPCION
                SET fecha_fin = DATEADD(DAY, 30, COALESCE(fecha_fin, GETDATE())), 
                    estado = 'Activa',
                    tipo_plan = 'Premium'
                WHERE id_suscripcion = @id_suscripcion
                UPDATE negocio.USUARIO
                SET id_rol = 4
                WHERE id_usuario = @id_usuario
                SET @tipo_notif = 'Renovacion'
                SET @msg = 'Tu suscripcion Premium ha sido renovada por 30 dias adicionales.'
            END
            ELSE
            BEGIN
                UPDATE negocio.SUSCRIPCION
                SET estado = 'Vencida',
                    tipo_plan = 'Gratuito'
                WHERE id_suscripcion = @id_suscripcion
                UPDATE negocio.USUARIO
                SET id_rol = 3
                WHERE id_usuario = @id_usuario
                SET @tipo_notif = 'Pago Fallido'
                SET @msg = 'No pudimos procesar tu pago. Tu suscripcion ha sido suspendida.'
            END
            INSERT INTO negocio.NOTIFICACION (id_usuario, tipo, mensaje)
            VALUES (@id_usuario, @tipo_notif, @msg)
        COMMIT
        RETURN 0
    END TRY
    BEGIN CATCH
        ROLLBACK
        ;THROW
    END CATCH
END
GO
CREATE OR ALTER PROCEDURE negocio.sp_NotificarSuscripcionesProximas
AS BEGIN
    SET NOCOUNT ON
    DECLARE @id_usuario INT
    DECLARE @nombre     VARCHAR(100)
    DECLARE @tipo_plan  VARCHAR(20)
    DECLARE @fecha_fin  DATE
    DECLARE @dias_rest  INT
    DECLARE @mensaje    VARCHAR(500)
    DECLARE cur_subs CURSOR FOR
        SELECT U.id_usuario, U.nombre_usuario, S.tipo_plan, S.fecha_fin,
               DATEDIFF(DAY, GETDATE(), S.fecha_fin)
        FROM negocio.SUSCRIPCION S
        INNER JOIN negocio.USUARIO U ON S.id_usuario = U.id_usuario
        WHERE S.estado = 'Activa'
          AND DATEDIFF(DAY, GETDATE(), S.fecha_fin) BETWEEN 0 AND 7
    OPEN cur_subs
    FETCH NEXT FROM cur_subs INTO @id_usuario, @nombre, @tipo_plan, @fecha_fin, @dias_rest
    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @mensaje = 'Hola ' + @nombre + ', tu plan ' + @tipo_plan +
                       ' vence en ' + CAST(@dias_rest AS VARCHAR) +
                       ' dias (' + CAST(@fecha_fin AS VARCHAR) + '). Renueva ahora.'
        IF NOT EXISTS (
            SELECT 1 FROM negocio.NOTIFICACION
            WHERE id_usuario = @id_usuario AND tipo = 'Vencimiento Proximo'
              AND CAST(fecha_envio AS DATE) = CAST(GETDATE() AS DATE)
        )
        BEGIN
            INSERT INTO negocio.NOTIFICACION (id_usuario, tipo, mensaje)
            VALUES (@id_usuario, 'Vencimiento Proximo', @mensaje)
        END
        FETCH NEXT FROM cur_subs INTO @id_usuario, @nombre, @tipo_plan, @fecha_fin, @dias_rest
    END
    CLOSE cur_subs
    DEALLOCATE cur_subs
END
GO
CREATE OR ALTER PROCEDURE negocio.sp_ReporteCanciones AS
BEGIN
    SELECT TOP 10
        C.titulo_cancion     AS Cancion,
        A.nombre_artistico   AS Artista,
        AL.titulo_album      AS Album,
        C.num_reproducciones AS Reproducciones
    FROM catalogo.CANCION C
    INNER JOIN catalogo.ARTISTA A  ON C.id_artista = A.id_artista
    INNER JOIN catalogo.ALBUM   AL ON C.id_album   = AL.id_album
    WHERE C.estado = 'Activo'
    ORDER BY C.num_reproducciones DESC
END
GO
CREATE OR ALTER PROCEDURE negocio.sp_ReporteArtistasPopulares AS
BEGIN
    SELECT
        A.nombre_artistico        AS Artista,
        A.pais                    AS Pais,
        SUM(C.num_reproducciones) AS TotalReproducciones
    FROM catalogo.ARTISTA A
    INNER JOIN catalogo.CANCION C ON A.id_artista = C.id_artista
    GROUP BY A.nombre_artistico, A.pais
    ORDER BY TotalReproducciones DESC
END
GO
CREATE OR ALTER PROCEDURE negocio.sp_ReporteHistorialUsuario
    @id_usuario   INT,
    @fecha_inicio DATE = NULL,
    @fecha_fin    DATE = NULL
AS BEGIN
    SELECT
        U.nombre_usuario     AS Usuario,
        C.titulo_cancion     AS Cancion,
        A.nombre_artistico   AS Artista,
        H.fecha_hora         AS FechaHora,
        H.duracion_escuchada AS Segundos
    FROM negocio.HISTORIAL_REPRODUCCION H
    INNER JOIN negocio.USUARIO  U ON H.id_usuario = U.id_usuario
    INNER JOIN catalogo.CANCION C ON H.id_cancion = C.id_cancion
    INNER JOIN catalogo.ARTISTA A ON C.id_artista = A.id_artista
    WHERE H.id_usuario = @id_usuario
      AND (@fecha_inicio IS NULL OR CAST(H.fecha_hora AS DATE) >= @fecha_inicio)
      AND (@fecha_fin   IS NULL OR CAST(H.fecha_hora AS DATE) <= @fecha_fin)
    ORDER BY H.fecha_hora DESC
END
GO
CREATE OR ALTER PROCEDURE negocio.sp_ReporteSuscripcionesActivas AS
BEGIN
    SELECT
        U.nombre_usuario                      AS Nombre,
        U.email_usuario                       AS Email,
        S.tipo_plan                           AS [Plan],
        S.fecha_inicio                        AS Inicio,
        S.fecha_fin                           AS Vencimiento,
        DATEDIFF(DAY, GETDATE(), S.fecha_fin) AS DiasRestantes
    FROM negocio.SUSCRIPCION S
    INNER JOIN negocio.USUARIO U ON S.id_usuario = U.id_usuario
    WHERE S.estado = 'Activa'
    ORDER BY S.fecha_fin
END
GO
CREATE OR ALTER PROCEDURE negocio.sp_ReporteIngresosArtista
    @id_artista INT
AS BEGIN
    SELECT
        A.nombre_artistico AS Artista,
        R.periodo          AS Periodo,
        R.total_reprod     AS Reproducciones,
        R.monto_calculado  AS MontoUSD
    FROM negocio.REGALIAS R
    INNER JOIN catalogo.ARTISTA A ON R.id_artista = A.id_artista
    WHERE R.id_artista = @id_artista
    ORDER BY R.periodo DESC
END
GO
CREATE OR ALTER PROCEDURE negocio.sp_ReporteAlbumesGuardados
    @id_usuario INT
AS BEGIN
    SELECT
        U.nombre_usuario   AS Usuario,
        AL.titulo_album    AS Album,
        A.nombre_artistico AS Artista,
        AG.fecha_guardado  AS FechaGuardado
    FROM negocio.ALBUM_GUARDADO AG
    INNER JOIN negocio.USUARIO  U  ON AG.id_usuario = U.id_usuario
    INNER JOIN catalogo.ALBUM   AL ON AG.id_album   = AL.id_album
    INNER JOIN catalogo.ARTISTA A  ON AL.id_artista = A.id_artista
    WHERE AG.id_usuario = @id_usuario
    ORDER BY AG.fecha_guardado DESC
END
GO
CREATE OR ALTER FUNCTION negocio.fn_ObtenerPlanActivo(@id_usuario INT)
RETURNS VARCHAR(20)
AS BEGIN
    DECLARE @plan VARCHAR(20)
    SELECT TOP 1 @plan = tipo_plan
    FROM negocio.SUSCRIPCION
    WHERE id_usuario = @id_usuario AND estado = 'Activa'
    ORDER BY fecha_fin DESC
    RETURN ISNULL(@plan, 'Gratuito')
END
GO
CREATE OR ALTER TRIGGER negocio.TR_SeguimientoArtista_Notificacion
ON negocio.SEGUIMIENTO_ARTISTA
AFTER INSERT
AS BEGIN
    SET NOCOUNT ON
    INSERT INTO negocio.NOTIFICACION (id_usuario, tipo, mensaje)
    SELECT I.id_usuario,
           'Nuevo Seguimiento',
           'Ahora sigues a ' + A.nombre_artistico + '. Seras el primero en recibir sus novedades.'
    FROM inserted I
    INNER JOIN catalogo.ARTISTA A ON I.id_artista = A.id_artista
END
GO
CREATE OR ALTER TRIGGER negocio.TR_Historial_ActualizarContador
ON negocio.HISTORIAL_REPRODUCCION
AFTER INSERT
AS BEGIN
    SET NOCOUNT ON
    UPDATE catalogo.CANCION
    SET num_reproducciones = num_reproducciones + 1
    WHERE id_cancion IN (SELECT id_cancion FROM inserted)
END
GO
CREATE OR ALTER PROCEDURE negocio.usp_RegistrarModificarUsuario
    @id_usuario INT,
    @nombre VARCHAR(100),
    @email VARCHAR(150),
    @telefono VARCHAR(20),
    @pais VARCHAR(80),
    @accion VARCHAR(10)
AS
BEGIN
    SET NOCOUNT ON
    IF @accion = 'SAVE'
    BEGIN
        IF @id_usuario IS NULL OR @id_usuario = 0
        BEGIN
            INSERT INTO negocio.USUARIO (id_rol, nombre_usuario, email_usuario, contrasena, telefono, pais, estado)
            VALUES (3, @nombre, @email, 'hash_default123', @telefono, @pais, 'Activo')
        END
        ELSE
        BEGIN
            UPDATE negocio.USUARIO
            SET nombre_usuario = @nombre,
                email_usuario = @email,
                telefono = @telefono,
                pais = @pais
            WHERE id_usuario = @id_usuario
        END
    END
    ELSE IF @accion = 'DELETE'
    BEGIN
        BEGIN TRY
            BEGIN TRAN
            UPDATE negocio.USUARIO
            SET estado = 'Inactivo'
            WHERE id_usuario = @id_usuario
            COMMIT TRAN
        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK TRAN
            THROW
        END CATCH
    END
END
GO
EXEC negocio.sp_CalcularRegalias 1, '2026-01'
EXEC negocio.sp_CalcularRegalias 2, '2026-01'
EXEC negocio.sp_CalcularRegalias 3, '2026-01'
EXEC negocio.sp_CalcularRegalias 4, '2026-01'
EXEC negocio.sp_CalcularRegalias 5, '2026-01'
EXEC negocio.sp_CalcularRegalias 6, '2026-01'
EXEC negocio.sp_CalcularRegalias 7, '2026-01'
EXEC negocio.sp_CalcularRegalias 8, '2026-01'
EXEC negocio.sp_CalcularRegalias 9, '2026-01'
EXEC negocio.sp_CalcularRegalias 10,'2026-01'
EXEC negocio.sp_CalcularRegalias 1, '2026-02'
EXEC negocio.sp_CalcularRegalias 2, '2026-02'
EXEC negocio.sp_CalcularRegalias 3, '2026-02'
EXEC negocio.sp_CalcularRegalias 4, '2026-02'
EXEC negocio.sp_CalcularRegalias 5, '2026-02'
EXEC negocio.sp_CalcularRegalias 6, '2026-02'
EXEC negocio.sp_CalcularRegalias 7, '2026-02'
EXEC negocio.sp_CalcularRegalias 8, '2026-02'
EXEC negocio.sp_CalcularRegalias 9, '2026-02'
EXEC negocio.sp_CalcularRegalias 10,'2026-02'
EXEC negocio.sp_CalcularRegalias 1, '2026-03'
EXEC negocio.sp_CalcularRegalias 2, '2026-03'
EXEC negocio.sp_CalcularRegalias 3, '2026-03'
EXEC negocio.sp_CalcularRegalias 4, '2026-03'
EXEC negocio.sp_CalcularRegalias 5, '2026-03'
EXEC negocio.sp_CalcularRegalias 6, '2026-03'
EXEC negocio.sp_CalcularRegalias 7, '2026-03'
EXEC negocio.sp_CalcularRegalias 8, '2026-03'
EXEC negocio.sp_CalcularRegalias 9, '2026-03'
EXEC negocio.sp_CalcularRegalias 10,'2026-03'
EXEC negocio.sp_CalcularRegalias 1, '2026-04'
EXEC negocio.sp_CalcularRegalias 2, '2026-04'
EXEC negocio.sp_CalcularRegalias 3, '2026-04'
EXEC negocio.sp_CalcularRegalias 4, '2026-04'
EXEC negocio.sp_CalcularRegalias 5, '2026-04'
EXEC negocio.sp_CalcularRegalias 6, '2026-04'
EXEC negocio.sp_CalcularRegalias 7, '2026-04'
EXEC negocio.sp_CalcularRegalias 8, '2026-04'
EXEC negocio.sp_CalcularRegalias 9, '2026-04'
EXEC negocio.sp_CalcularRegalias 10,'2026-04'
GO
EXEC negocio.sp_NotificarSuscripcionesProximas
GO
EXEC negocio.sp_ReporteCanciones
GO
EXEC negocio.sp_ReporteArtistasPopulares
GO
EXEC negocio.sp_ReporteHistorialUsuario @id_usuario = 12, @fecha_inicio = '2026-01-01', @fecha_fin = '2026-04-30'
GO
EXEC negocio.sp_ReporteSuscripcionesActivas
GO
EXEC negocio.sp_ReporteIngresosArtista @id_artista = 1
GO
EXEC negocio.sp_ReporteIngresosArtista @id_artista = 5
GO
EXEC negocio.sp_ReporteIngresosArtista @id_artista = 6
GO
EXEC negocio.sp_ReporteIngresosArtista @id_artista = 7
GO
EXEC negocio.sp_ReporteIngresosArtista @id_artista = 8
GO
EXEC negocio.sp_ReporteIngresosArtista @id_artista = 9
GO
EXEC negocio.sp_ReporteIngresosArtista @id_artista = 10
GO
EXEC negocio.sp_ReporteAlbumesGuardados @id_usuario = 12
GO
SELECT negocio.fn_ObtenerPlanActivo(13) AS PlanUsuario13
SELECT negocio.fn_ObtenerPlanActivo(12) AS PlanUsuario12
GO
EXEC negocio.sp_RegistrarReproduccion @id_usuario = 12, @id_cancion = 5, @duracion = 247
GO
EXEC negocio.sp_ProcesarRenovacion @id_suscripcion = 1, @estado_pago = 'Completado', @metodo = 'PayPal'
GO
EXEC negocio.sp_ProcesarRenovacion @id_suscripcion = 2, @estado_pago = 'Fallido', @metodo = 'Tarjeta Credito'
GO
UPDATE negocio.NOTIFICACION SET leida = 1 WHERE id_notificacion = 1
GO
DELETE FROM negocio.PLAYLIST_CANCION WHERE id_playlist = 1 AND id_cancion = 2
GO
UPDATE negocio.USUARIO SET estado = 'Inactivo' WHERE id_usuario = 22
GO
UPDATE negocio.USUARIO SET estado = 'Activo'   WHERE id_usuario = 22
GO
EXEC negocio.sp_RegistrarReproduccion @id_usuario=6, @id_cancion=1, @duracion=188
SELECT TOP 1 * FROM negocio.HISTORIAL_REPRODUCCION ORDER BY id_historial DESC
SELECT num_reproducciones FROM catalogo.CANCION WHERE id_cancion=1
GO
BEGIN TRY
    EXEC negocio.sp_RegistrarReproduccion @id_usuario=6, @id_cancion=9999, @duracion=100
END TRY
BEGIN CATCH
    PRINT 'ROLLBACK OK: ' + ERROR_MESSAGE()
END CATCH
GO
EXEC negocio.sp_CalcularRegalias @id_artista=1, @periodo='2026-01'
SELECT * FROM negocio.REGALIAS WHERE id_artista=1 AND periodo='2026-01'
GO
EXEC negocio.sp_CalcularRegalias @id_artista=1, @periodo='2026-01'
SELECT COUNT(*) AS TotalRegalias FROM negocio.REGALIAS WHERE id_artista=1 AND periodo='2026-01'
GO
SELECT fecha_fin, estado FROM negocio.SUSCRIPCION WHERE id_suscripcion=1
EXEC negocio.sp_ProcesarRenovacion @id_suscripcion=1, @estado_pago='Completado', @metodo='PayPal'
SELECT fecha_fin, estado FROM negocio.SUSCRIPCION WHERE id_suscripcion=1
SELECT TOP 1 tipo, mensaje FROM negocio.NOTIFICACION ORDER BY id_notificacion DESC
GO
EXEC negocio.sp_ProcesarRenovacion @id_suscripcion=2, @estado_pago='Fallido'
SELECT estado FROM negocio.SUSCRIPCION WHERE id_suscripcion=2
SELECT TOP 1 tipo FROM negocio.NOTIFICACION ORDER BY id_notificacion DESC
GO
INSERT INTO negocio.SUSCRIPCION (id_usuario, tipo_plan, fecha_inicio, fecha_fin)
VALUES (20, 'Premium', DATEADD(DAY,-27,GETDATE()), DATEADD(DAY,3,GETDATE()))
GO
EXEC negocio.sp_NotificarSuscripcionesProximas
SELECT TOP 3 tipo, mensaje FROM negocio.NOTIFICACION ORDER BY id_notificacion DESC
GO
EXEC negocio.sp_NotificarSuscripcionesProximas
SELECT COUNT(*) AS Duplicados FROM negocio.NOTIFICACION
WHERE tipo='Vencimiento Proximo' AND CAST(fecha_envio AS DATE)=CAST(GETDATE() AS DATE)
GO
SELECT negocio.fn_ObtenerPlanActivo(13) AS PlanUsuario13
SELECT negocio.fn_ObtenerPlanActivo(12) AS PlanUsuario12
SELECT negocio.fn_ObtenerPlanActivo(16) AS PlanUsuario16
GO
INSERT INTO negocio.SEGUIMIENTO_ARTISTA (id_usuario, id_artista) VALUES (20, 3)
SELECT TOP 1 tipo, mensaje FROM negocio.NOTIFICACION ORDER BY id_notificacion DESC
GO
BEGIN TRY
    INSERT INTO negocio.USUARIO (id_rol, nombre_usuario, email_usuario, contrasena, estado)
    VALUES (3, 'Test', 'test@sw.ec', 'hash_test', 'Suspendido')
END TRY
BEGIN CATCH
    PRINT 'CK_USUARIO_ESTADO OK: ' + ERROR_MESSAGE()
END CATCH
GO
BEGIN TRY
    INSERT INTO negocio.PAGO (id_suscripcion, monto, metodo_pago) VALUES (1, -5.00, 'Tarjeta')
END TRY
BEGIN CATCH
    PRINT 'CK_PAGO_MONTO OK: ' + ERROR_MESSAGE()
END CATCH
GO
BEGIN TRY
    INSERT INTO catalogo.CANCION (id_album, id_artista, titulo_cancion, duracion_seg)
    VALUES (1, 1, 'Cancion Test', 0)
END TRY
BEGIN CATCH
    PRINT 'CK_CANCION_DURACION OK: ' + ERROR_MESSAGE()
END CATCH
GO
EXEC sp_helpconstraint 'catalogo.CANCION'
GO
EXEC sp_helpconstraint 'negocio.USUARIO'
GO
UPDATE catalogo.CANCION SET num_reproducciones = 3900000000 WHERE titulo_cancion = 'Shape of You'
UPDATE catalogo.CANCION SET num_reproducciones = 3400000000 WHERE titulo_cancion = 'Blinding Lights'
UPDATE catalogo.CANCION SET num_reproducciones = 1400000000 WHERE titulo_cancion = 'Titi Me Pregunto'
UPDATE catalogo.CANCION SET num_reproducciones = 950000000 WHERE titulo_cancion = 'TQG'
UPDATE catalogo.CANCION SET num_reproducciones = 450000000 WHERE titulo_cancion = 'Rosas'
UPDATE catalogo.CANCION SET num_reproducciones = 120000000 WHERE titulo_cancion = 'Loves a Stranger'
UPDATE catalogo.CANCION SET num_reproducciones = 95000000 WHERE titulo_cancion = 'La Playa'
UPDATE catalogo.CANCION SET num_reproducciones = 85000000 WHERE titulo_cancion = 'Follow the Sun'
UPDATE catalogo.CANCION SET num_reproducciones = 70000000 WHERE titulo_cancion = '20 de Enero'
UPDATE catalogo.CANCION SET num_reproducciones = 65000000 WHERE titulo_cancion = 'El Triste'
UPDATE catalogo.CANCION SET num_reproducciones = 45000000 WHERE titulo_cancion = 'Summer Sun'
UPDATE catalogo.CANCION SET num_reproducciones = 30000000 WHERE titulo_cancion = 'Mazuka'
UPDATE catalogo.CANCION SET num_reproducciones = 25000000 WHERE titulo_cancion = 'Almohada'
UPDATE catalogo.CANCION SET num_reproducciones = 20000000 WHERE titulo_cancion = 'Gavilán o Paloma'
UPDATE catalogo.CANCION SET num_reproducciones = 18000000 WHERE titulo_cancion = 'La Nave del Olvido'
GO
INSERT INTO negocio.HISTORIAL_REPRODUCCION (id_usuario, id_cancion, fecha_hora, duracion_escuchada) VALUES (12, (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = 'Shape of You'), GETDATE(), 233)
INSERT INTO negocio.HISTORIAL_REPRODUCCION (id_usuario, id_cancion, fecha_hora, duracion_escuchada) VALUES (12, (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = 'Loves a Stranger'), DATEADD(MINUTE, -5, GETDATE()), 240)
INSERT INTO negocio.HISTORIAL_REPRODUCCION (id_usuario, id_cancion, fecha_hora, duracion_escuchada) VALUES (12, (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = 'Mazuka'), DATEADD(MINUTE, -10, GETDATE()), 210)
INSERT INTO negocio.HISTORIAL_REPRODUCCION (id_usuario, id_cancion, fecha_hora, duracion_escuchada) VALUES (12, (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = 'Follow the Sun'), DATEADD(MINUTE, -15, GETDATE()), 195)
GO
SELECT * FROM negocio.USUARIO
SELECT * FROM catalogo.ARTISTA
SELECT * FROM catalogo.CANCION ORDER BY num_reproducciones DESC
SELECT * FROM negocio.HISTORIAL_REPRODUCCION
SELECT * FROM negocio.SUSCRIPCION
SELECT * FROM negocio.PAGO
SELECT * FROM negocio.REGALIAS ORDER BY id_artista, periodo
SELECT * FROM negocio.ALBUM_GUARDADO
SELECT * FROM negocio.NOTIFICACION
GO
INSERT INTO catalogo.GENERO (nombre_genero, descripcion) VALUES
    (N'Jazz',             N'Musica de improvisacion y swing de origen norteamericano'),
    (N'Pop Retro',        N'Pop de decadas pasadas con estetica vintage'),
    (N'Pop Actual',       N'Pop contemporaneo de exito global en la actualidad'),
    (N'Indie Riot',       N'Indie alternativo de alta carga emocional y sonido crudo'),
    (N'Indie Rock',       N'Rock independiente de produccion alternativa'),
    (N'Pop Alternativo',  N'Pop con influencias alternativas e independientes'),
    (N'Synth-Pop',        N'Pop sintetizado de inspiracion ochentosa y electronica'),
    (N'Bolero',           N'Genero romantico latinoamericano de profundo lirismo'),
    (N'Indie Pop',        N'Pop independiente de sonido intimo y lirica introspectiva'),
    (N'Folk Alternativo', N'Folk moderno con produccion alternativa y letras poeticas')
GO
INSERT INTO negocio.USUARIO (id_rol, nombre_usuario, email_usuario, contrasena, estado) VALUES
    (2, N'Zoé Banda',        N'zoe@soundwave.ec',          N'hash_zoe01',   N'Activo'),
    (2, N'Videoclub Duo',    N'videoclub@soundwave.ec',    N'hash_vclub02', N'Activo'),
    (2, N'Michael Jackson',  N'mj@soundwave.ec',           N'hash_mj03',    N'Activo'),
    (2, N'Julio Jaramillo',  N'jjaramillo@soundwave.ec',   N'hash_jjar04',  N'Activo'),
    (2, N'Josean Log',       N'joseanlog@soundwave.ec',    N'hash_jlog01',  N'Activo')
GO
DECLARE @uid_zoe   INT = (SELECT id_usuario FROM negocio.USUARIO WHERE email_usuario = N'zoe@soundwave.ec')
DECLARE @uid_vclub INT = (SELECT id_usuario FROM negocio.USUARIO WHERE email_usuario = N'videoclub@soundwave.ec')
DECLARE @uid_mj    INT = (SELECT id_usuario FROM negocio.USUARIO WHERE email_usuario = N'mj@soundwave.ec')
DECLARE @uid_jj    INT = (SELECT id_usuario FROM negocio.USUARIO WHERE email_usuario = N'jjaramillo@soundwave.ec')
DECLARE @uid_jlog  INT = (SELECT id_usuario FROM negocio.USUARIO WHERE email_usuario = N'joseanlog@soundwave.ec')

INSERT INTO catalogo.ARTISTA (id_usuario, nombre_artistico, pais, fecha_debut) VALUES
    (@uid_zoe,   N'Zoé',             N'Mexico',   N'2000-01-01'),
    (@uid_vclub, N'Videoclub',       N'Francia',  N'2018-01-01'),
    (@uid_mj,    N'Michael Jackson', N'USA',      N'1964-07-26'),
    (@uid_jj,    N'Julio Jaramillo', N'Ecuador',  N'1950-01-01'),
    (@uid_jlog,  N'Josean Log',      N'Mexico',   N'2015-01-01')
GO
DECLARE @art_zoe   INT = (SELECT id_artista FROM catalogo.ARTISTA WHERE nombre_artistico = N'Zoé')
DECLARE @art_vclub INT = (SELECT id_artista FROM catalogo.ARTISTA WHERE nombre_artistico = N'Videoclub')
DECLARE @art_mj    INT = (SELECT id_artista FROM catalogo.ARTISTA WHERE nombre_artistico = N'Michael Jackson')
DECLARE @art_jj    INT = (SELECT id_artista FROM catalogo.ARTISTA WHERE nombre_artistico = N'Julio Jaramillo')
DECLARE @art_jlog  INT = (SELECT id_artista FROM catalogo.ARTISTA WHERE nombre_artistico = N'Josean Log')

INSERT INTO catalogo.ALBUM (id_artista, titulo_album, fecha_lanzamiento) VALUES
    (@art_zoe,   N'Memo Rex Commander y el Corazón Atómico de la Vía Láctea', N'2006-06-06'),
    (@art_vclub, N'Amour Plastique EP',       N'2018-10-05'),
    (@art_mj,    N'Thriller',                 N'1982-11-30'),
    (@art_jj,    N'Nuestro Juramento',        N'1960-01-01'),
    (@art_jlog,  N'Háblate de Mí',            N'2019-04-12')
GO
DECLARE @art_zoe   INT = (SELECT id_artista FROM catalogo.ARTISTA WHERE nombre_artistico = N'Zoé')
DECLARE @art_vclub INT = (SELECT id_artista FROM catalogo.ARTISTA WHERE nombre_artistico = N'Videoclub')
DECLARE @art_mj    INT = (SELECT id_artista FROM catalogo.ARTISTA WHERE nombre_artistico = N'Michael Jackson')
DECLARE @art_jj    INT = (SELECT id_artista FROM catalogo.ARTISTA WHERE nombre_artistico = N'Julio Jaramillo')
DECLARE @art_jlog  INT = (SELECT id_artista FROM catalogo.ARTISTA WHERE nombre_artistico = N'Josean Log')

DECLARE @alb_zoe   INT = (SELECT id_album FROM catalogo.ALBUM WHERE id_artista = @art_zoe AND titulo_album = N'Memo Rex Commander y el Corazón Atómico de la Vía Láctea')
DECLARE @alb_vclub INT = (SELECT id_album FROM catalogo.ALBUM WHERE id_artista = @art_vclub)
DECLARE @alb_mj    INT = (SELECT id_album FROM catalogo.ALBUM WHERE id_artista = @art_mj AND titulo_album = N'Thriller')
DECLARE @alb_jj    INT = (SELECT id_album FROM catalogo.ALBUM WHERE id_artista = @art_jj AND titulo_album = N'Nuestro Juramento')
DECLARE @alb_jlog  INT = (SELECT id_album FROM catalogo.ALBUM WHERE id_artista = @art_jlog AND titulo_album = N'Háblate de Mí')

INSERT INTO catalogo.CANCION (id_album, id_artista, titulo_cancion, duracion_seg, url_audio, num_reproducciones, fecha_publicacion) VALUES
    (@alb_zoe,   @art_zoe,   N'Soñé',            255, N'/audio/sone.mp3',              180000000,   N'2006-06-06'),
    (@alb_zoe,   @art_zoe,   N'Labios Rotos',     241, N'/audio/labios_rotos.mp3',     145000000,   N'2006-06-06'),
    (@alb_zoe,   @art_zoe,   N'Luna',             263, N'/audio/luna.mp3',              98000000,   N'2006-06-06'),
    (@alb_vclub, @art_vclub, N'Amour Plastique',  231, N'/audio/amour_plastique.mp3',   95000000,   N'2018-10-05'),
    (@alb_vclub, @art_vclub, N'En nuit',          219, N'/audio/en_nuit.mp3',           61000000,   N'2019-02-14'),
    (@alb_mj,    @art_mj,    N'Billie Jean',      294, N'/audio/billie_jean.mp3',    2900000000,    N'1983-01-02'),
    (@alb_mj,    @art_mj,    N'Beat It',          258, N'/audio/beat_it.mp3',        1800000000,    N'1983-02-14'),
    (@alb_mj,    @art_mj,    N'Thriller',         358, N'/audio/thriller.mp3',       1600000000,    N'1983-11-11'),
    (@alb_jj,    @art_jj,    N'Nuestro Juramento',198, N'/audio/nuestro_juramento.mp3', 55000000,   N'1960-01-01'),
    (@alb_jj,    @art_jj,    N'Ódiame',           210, N'/audio/odiame.mp3',            38000000,   N'1958-01-01'),
    (@alb_jlog,  @art_jlog,  N'Chachachá',        208, N'/audio/chachacha.mp3',         42000000,   N'2019-04-12'),
    (@alb_jlog,  @art_jlog,  N'Jacaranda',        224, N'/audio/jacaranda.mp3',         28000000,   N'2020-03-10'),
    (@alb_jlog,  @art_jlog,  N'Beso',             197, N'/audio/beso.mp3',              19000000,   N'2021-07-22')
GO
DECLARE @id_jazz         INT = (SELECT id_genero FROM catalogo.GENERO WHERE nombre_genero = N'Jazz')
DECLARE @id_pop_actual   INT = (SELECT id_genero FROM catalogo.GENERO WHERE nombre_genero = N'Pop Actual')
DECLARE @id_indie_riot   INT = (SELECT id_genero FROM catalogo.GENERO WHERE nombre_genero = N'Indie Riot')
DECLARE @id_indie_rock   INT = (SELECT id_genero FROM catalogo.GENERO WHERE nombre_genero = N'Indie Rock')
DECLARE @id_synth_pop    INT = (SELECT id_genero FROM catalogo.GENERO WHERE nombre_genero = N'Synth-Pop')
DECLARE @id_pop_retro    INT = (SELECT id_genero FROM catalogo.GENERO WHERE nombre_genero = N'Pop Retro')
DECLARE @id_bolero       INT = (SELECT id_genero FROM catalogo.GENERO WHERE nombre_genero = N'Bolero')
DECLARE @id_indie_pop    INT = (SELECT id_genero FROM catalogo.GENERO WHERE nombre_genero = N'Indie Pop')

DECLARE @can_shape    INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Shape of You')
DECLARE @can_loves    INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Loves a Stranger')
DECLARE @can_mazuka   INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Mazuka')
DECLARE @can_follow   INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Follow the Sun')
DECLARE @can_sone     INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Soñé')
DECLARE @can_labios   INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Labios Rotos')
DECLARE @can_luna     INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Luna')
DECLARE @can_amour    INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Amour Plastique')
DECLARE @can_nuit     INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'En nuit')
DECLARE @can_billie   INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Billie Jean')
DECLARE @can_beatit   INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Beat It')
DECLARE @can_thriller INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Thriller')
DECLARE @can_nuestro  INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Nuestro Juramento')
DECLARE @can_odiame   INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Ódiame')
DECLARE @can_chach    INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Chachachá')
DECLARE @can_jacaran  INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Jacaranda')
DECLARE @can_beso     INT = (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Beso')

INSERT INTO catalogo.CANCION_GENERO (id_cancion, id_genero) VALUES
    (@can_shape,    @id_pop_actual),
    (@can_loves,    @id_indie_riot),
    (@can_mazuka,   @id_indie_riot),
    (@can_follow,   @id_jazz),
    (@can_sone,     @id_indie_rock),
    (@can_labios,   @id_indie_rock),
    (@can_luna,     @id_indie_rock),
    (@can_amour,    @id_synth_pop),
    (@can_nuit,     @id_synth_pop),
    (@can_billie,   @id_pop_retro),
    (@can_beatit,   @id_pop_retro),
    (@can_thriller, @id_pop_retro),
    (@can_nuestro,  @id_bolero),
    (@can_odiame,   @id_bolero),
    (@can_chach,    @id_indie_pop),
    (@can_jacaran,  @id_indie_pop),
    (@can_beso,     @id_indie_pop)
GO
UPDATE catalogo.CANCION
SET titulo_cancion = N'Gavilán o Paloma'
WHERE id_cancion = 9
GO
INSERT INTO negocio.HISTORIAL_REPRODUCCION (id_usuario, id_cancion, fecha_hora, duracion_escuchada) VALUES
    (12, (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Shape of You'),    GETDATE(),                      233),
    (12, (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Loves a Stranger'), DATEADD(MINUTE, -5, GETDATE()), 240),
    (12, (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Mazuka'),           DATEADD(MINUTE,-10, GETDATE()), 210),
    (12, (SELECT id_cancion FROM catalogo.CANCION WHERE titulo_cancion = N'Follow the Sun'),   DATEADD(MINUTE,-15, GETDATE()), 195)
GO
