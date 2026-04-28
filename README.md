# lqb — Liquibase Assistant CLI

> CLI interattiva per Liquibase: gestione ambienti, esecuzione guidata dei comandi, monitoraggio dello stato del database e protezione degli ambienti di produzione.

---

## Introduzione (Italiano)

### Cos'è lqb?

`lqb` è una CLI costruita sopra Liquibase OSS che semplifica la gestione delle migrazioni del database. Non sostituisce Liquibase — lo avvolge aggiungendo:

- **Profili di connessione** con password salvate nel portachiavi del sistema operativo
- **Protezione degli ambienti** — gli ambienti contrassegnati come `protected` richiedono una conferma esplicita prima di operazioni distruttive
- **Builder guidato** interattivo per costruire comandi senza ricordare la sintassi
- **Anteprima SQL** prima di applicare qualsiasi migrazione
- **Dashboard live** con stato dei changeset, cronologia e lock attivi
- **Installer automatico** che scarica Liquibase OSS e i driver JDBC mancanti

### Prerequisiti

- Python 3.11 o superiore
- Java 11 o superiore (sul PATH)
- Connessione internet (solo per la prima installazione)

### Installazione

**1. Clona o scarica il progetto**

```bash
git clone <url-repository>
cd "CLI Liquibase"
```

**2. Esegui l'installer**

```bash
python install.py
```

L'installer si occupa di:
- Verificare la versione di Python e Java
- Scaricare Liquibase OSS 5.0.2 in `~/.lqb/bin/`
- Scaricare i driver JDBC (PostgreSQL, MySQL, MariaDB)
- Installare il pacchetto Python `lqb`

Al termine, il comando `lqb` è disponibile globalmente nel terminale.

**3. Verifica l'installazione**

```bash
lqb --help
```

### Configurazione del primo profilo

Un profilo contiene i dati di connessione a un database. La password viene salvata nel portachiavi del sistema operativo (mai in chiaro su disco).

```bash
lqb env add
```

Seguire i prompt:
- **Nome profilo** — es. `local-pg`, `staging`, `production`
- **JDBC URL** — es. `jdbc:postgresql://localhost:5432/mydb`
- **Username**
- **Password** (salvata nel portachiavi)
- **Percorso del changelog** — es. `db/changelog/db.changelog-master.xml`
- **Schema di default** (opzionale)
- **Protetto?** — scegliere `Y` per gli ambienti di produzione

Verificare la connessione:

```bash
lqb env test
```

### Comandi disponibili

#### Gestione ambienti

```bash
lqb env list              # elenca tutti i profili
lqb env add               # aggiunge un nuovo profilo
lqb env use <nome>        # imposta il profilo attivo
lqb env test [nome]       # verifica la connessione
lqb env remove <nome>     # rimuove un profilo
```

#### Stato del database

```bash
lqb status                # changeset applicati e in attesa
lqb status --env staging  # specifica un ambiente
```

#### Applicare le migrazioni

```bash
lqb update                          # applica tutti i changeset in attesa
lqb update --preview                # mostra l'SQL senza applicarlo
lqb update --count 3                # applica solo i prossimi 3 changeset
lqb update --env staging            # specifica un ambiente
lqb update --yes                    # salta la conferma interattiva
```

#### Rollback

```bash
lqb rollback --count 1              # annulla l'ultimo changeset
lqb rollback --tag v1.0             # torna al tag specificato
lqb rollback --count 1 --preview    # mostra l'SQL di rollback senza eseguirlo
```

#### Validazione e anteprima

```bash
lqb validate                        # valida il changelog + lint locale
lqb validate --lint-only            # solo lint (nessuna chiamata a Liquibase)
```

#### Dashboard live

```bash
lqb dash                            # dashboard aggiornata ogni 5 secondi
lqb dash --refresh 10               # intervallo personalizzato in secondi
lqb dash --env production           # monitora un ambiente specifico
```

Premere `Ctrl+C` per uscire.

#### Builder guidato

```bash
lqb do
```

Modalità interattiva: selezionare il comando, configurare i parametri tramite prompt, vedere il comando risolto e confermare prima dell'esecuzione. Ideale per chi non ricorda la sintassi esatta o vuole un'anteprima SQL integrata.

### Protezione degli ambienti di produzione

I profili con `protected: true` richiedono di digitare il nome del profilo per confermare qualsiasi operazione distruttiva (update, rollback). Questo previene esecuzioni accidentali.

```bash
lqb env add
# ... inserire i dati ...
# Protetto? -> Y
```

### Struttura dei profili

I profili vengono salvati in `~/.lqb/profiles.yaml`. Esempio:

```yaml
active: local-pg

profiles:
  - name: local-pg
    jdbc_url: jdbc:postgresql://localhost:5432/mydb
    username: myuser
    changelog_file: db/changelog/db.changelog-master.xml
    protected: false

  - name: production
    jdbc_url: jdbc:postgresql://prod-host:5432/mydb
    username: produser
    changelog_file: db/changelog/db.changelog-master.xml
    protected: true
```

---

---

## Introduction (English)

### What is lqb?

`lqb` is a CLI built on top of Liquibase OSS that simplifies database migration management. It does not replace Liquibase — it wraps it and adds:

- **Connection profiles** with passwords stored in the OS keychain
- **Environment protection** — profiles marked as `protected` require explicit confirmation before destructive operations
- **Interactive guided builder** to construct commands without memorising syntax
- **SQL preview** before applying any migration
- **Live dashboard** showing changeset status, history, and active locks
- **Automatic installer** that downloads Liquibase OSS and missing JDBC drivers

### Prerequisites

- Python 3.11 or higher
- Java 11 or higher (on PATH)
- Internet connection (first install only)

### Installation

**1. Clone or download the project**

```bash
git clone <repository-url>
cd "CLI Liquibase"
```

**2. Run the installer**

```bash
python install.py
```

The installer will:
- Verify Python and Java versions
- Download Liquibase OSS 5.0.2 to `~/.lqb/bin/`
- Download JDBC drivers (PostgreSQL, MySQL, MariaDB)
- Install the `lqb` Python package

Once complete, the `lqb` command is available globally in the terminal.

**3. Verify the installation**

```bash
lqb --help
```

### Setting up your first profile

A profile holds the connection details for a database. The password is stored in the OS keychain — never written to disk in plain text.

```bash
lqb env add
```

Follow the prompts:
- **Profile name** — e.g. `local-pg`, `staging`, `production`
- **JDBC URL** — e.g. `jdbc:postgresql://localhost:5432/mydb`
- **Username**
- **Password** (stored in keychain)
- **Changelog file path** — e.g. `db/changelog/db.changelog-master.xml`
- **Default schema** (optional)
- **Protected?** — choose `Y` for production environments

Test the connection:

```bash
lqb env test
```

### Available commands

#### Environment management

```bash
lqb env list              # list all profiles
lqb env add               # add a new profile
lqb env use <name>        # set the active profile
lqb env test [name]       # test the connection
lqb env remove <name>     # remove a profile
```

#### Database status

```bash
lqb status                # applied and pending changesets
lqb status --env staging  # target a specific environment
```

#### Applying migrations

```bash
lqb update                          # apply all pending changesets
lqb update --preview                # show SQL without applying
lqb update --count 3                # apply only the next 3 changesets
lqb update --env staging            # target a specific environment
lqb update --yes                    # skip interactive confirmation
```

#### Rollback

```bash
lqb rollback --count 1              # undo the last changeset
lqb rollback --tag v1.0             # roll back to the specified tag
lqb rollback --count 1 --preview    # show rollback SQL without executing
```

#### Validation and preview

```bash
lqb validate                        # validate changelog + local lint
lqb validate --lint-only            # local lint only (no Liquibase call)
```

#### Live dashboard

```bash
lqb dash                            # dashboard refreshed every 5 seconds
lqb dash --refresh 10               # custom refresh interval in seconds
lqb dash --env production           # monitor a specific environment
```

Press `Ctrl+C` to exit.

#### Guided builder

```bash
lqb do
```

Interactive mode: select a command, configure parameters via prompts, review the resolved command, and confirm before execution. Ideal for anyone who does not remember exact syntax or wants an integrated SQL preview.

### Production environment protection

Profiles with `protected: true` require typing the profile name to confirm any destructive operation (update, rollback). This prevents accidental execution.

```bash
lqb env add
# ... enter connection details ...
# Protected? -> Y
```

### Profile structure

Profiles are stored in `~/.lqb/profiles.yaml`. Example:

```yaml
active: local-pg

profiles:
  - name: local-pg
    jdbc_url: jdbc:postgresql://localhost:5432/mydb
    username: myuser
    changelog_file: db/changelog/db.changelog-master.xml
    protected: false

  - name: production
    jdbc_url: jdbc:postgresql://prod-host:5432/mydb
    username: produser
    changelog_file: db/changelog/db.changelog-master.xml
    protected: true
```
