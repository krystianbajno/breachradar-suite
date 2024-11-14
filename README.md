[![CodeFactor](https://www.codefactor.io/repository/github/krystianbajno/breachradar-suite/badge)](https://www.codefactor.io/repository/github/krystianbajno/breachradar-suite)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/349279ed04b94323928355065a9ede7f)](https://app.codacy.com/gh/krystianbajno/breachradar-suite/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fkrystianbajno%2Fbreachradar-suite.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Fkrystianbajno%2Fbreachradar-suite?ref=badge_shield)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fkrystianbajno%2Fbreachradar-suite.svg?type=shield&issueType=security)](https://app.fossa.com/projects/git%2Bgithub.com%2Fkrystianbajno%2Fbreachradar-suite?ref=badge_shield&issueType=security)

# BreachRadar
```
    ____                       __    ____            __          
   / __ )________  ____ ______/ /_  / __ \____ _____/ /___ ______
  / __  / ___/ _ \/ __ `/ ___/ __ \/ /_/ / __ `/ __  / __ `/ ___/
 / /_/ / /  /  __/ /_/ / /__/ / / / _, _/ /_/ / /_/ / /_/ / /    
/_____/_/   \___/\__,_/\___/_/ /_/_/ |_|\__,_/\__,_/\__,_/_/     

                                              Krystian Bajno 2024
```

BreachRadar is an open-source Cyber Threat Intelligence (CTI) platform designed to collect and process data from various sources to detect potential security breaches and leaked credentials. It operates using Elasticsearch, PostgreSQL, SMB/min.io, and Kafka. The plugin-based system allows for integration of new collectors, processors, and data analysis tools.

<img src="https://raw.githubusercontent.com/krystianbajno/krystianbajno/main/img/breachradar-arch.png"/>

# Suite Commands
### Microradar
Swiss-army knife for credentials. A lightweight Rust CLI tool for local data ingestion and Elastic search using CLI, compatible with BreachRadar.

```bash
# commands/microradar
cd commands/microradar
cargo build --release
./microradar ingest <input directory> # ingest data from selected directory
./microradar search <searchterm> # search elastic using CLI
./microradar scan <file> # scan file for credentials inside.
./microradar scan <file> --offline # do not use postgreSQL when scanning
```

# Running
### Plugin Installation
Copy the plugin into `plugins/` directory. The framework will detect and run it automatically. To disable the plugin, navigate to plugin directory and edit `config.yaml`. Set `enabled` to `false`.

### Available plugins in core
**Due to sensitive nature of sources and operations, plugins are kept private and separate from core.**.
- **local_plugin** - Read data from the local storage - `./data/local_ingest` directory (default).

### Installation
0. Run `python3 -m venv venv`, `source venv/bin/activate`, and `pip install -r requirements.txt`
1. Run `docker-compose up` to start Kafka, PostgreSQL, and ElasticSearch.
2. Compile rust_bindings as they contain Rust PyO3, using `maturin build --release` and `pip install target/wheels/*.whl`.
3. Compile plugins if needed, as they may contain Rust PyO3, using `maturin build --release` and `pip install target/wheels/*.whl`.
4. Run `main.py` to setup the database, indexes, and start collection and processing services.
5. Run `npm install`, `npm run build`, and `npm run start` in `webui/` directory to start Web UI service.

You can distribute and scale these components on many machines in order to get a good performance through terabytes of data.

In order to disable processing or collection, modify `config.yaml` and set

```yaml
processing: false
# or
collecting: false
```

# Architecture Overview
The core system consists of the following main components:

- Collection and processing agent (`main.py`)
- ElasticSearch - Stores processed data and provides powerful search capabilities.
- Kafka - Is an event queue.
- min.io/SMB Server - Hosts scrapes data to process.
- PostgreSQL - Stores scrap metadata, tracks processing.
- WebUI - Allows to search and analyze data through a web interface connected to ElasticSearch.


# Technical details for development
### In order to develop a plugin
- Follow the directory structure of `local_plugin`.
- Collectors' classnames must end with `Collector`, Processors' classnames must end with `Processor`, Providers' classnames must end with `Provider`.
- Plugins must have a provider registering the plugin in `register` method and must extend `PluginProvider` class.
- In order to register and use a service inside plugin, use the `App` object passed to a plugin provider and the `.make()` and `.bind()` methods.

### Plugin `Collectors` and `Processors`
- Plugins can use `Core` components freely.
- Collectors implement **PluginCollectorInterface** and must define a `collect` method.
- Collectors implement **PluginCollectorInterface** and must define a `postprocess` method.
- Processors implement **PluginProcessorInterface** with `can_process` and `process` methods.
- Processors decide whether they can process a scrap based on `can_process`.

# TODO in core
- OpenCTI integration
- RecordedFuture integration
- Implement analysis and `basic_analysis` plugin.


## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fkrystianbajno%2Fbreachradar-suite.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fkrystianbajno%2Fbreachradar-suite?ref=badge_large)
