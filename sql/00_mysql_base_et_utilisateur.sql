-- =============================================================
-- Création de la base et de l'utilisateur de l'agent, en LECTURE SEULE
-- À exécuter en root sur MySQL / MariaDB (XAMPP), AVANT 01_schema.sql
-- Definir @agent_password dans la meme session avant ce script.
-- Injecter cette valeur depuis un secret externe, jamais depuis le depot.
-- =============================================================
CREATE DATABASE IF NOT EXISTS catalogue CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE catalogue;

SET @creation_utilisateur = CONCAT(
    'CREATE USER IF NOT EXISTS ''agent_ia''@''%'' IDENTIFIED BY ',
    QUOTE(@agent_password)
);
PREPARE creation_utilisateur FROM @creation_utilisateur;
EXECUTE creation_utilisateur;
DEALLOCATE PREPARE creation_utilisateur;

SET @creation_utilisateur = CONCAT(
    'CREATE USER IF NOT EXISTS ''agent_ia''@''localhost'' IDENTIFIED BY ',
    QUOTE(@agent_password)
);
PREPARE creation_utilisateur FROM @creation_utilisateur;
EXECUTE creation_utilisateur;
DEALLOCATE PREPARE creation_utilisateur;
GRANT SELECT ON catalogue.* TO 'agent_ia'@'%';
GRANT SELECT ON catalogue.* TO 'agent_ia'@'localhost';
FLUSH PRIVILEGES;
