# Goalcast

Football match analysis and MCP (Model Context Protocol) server — multi-provider data aggregation with LLM-powered analysis.

## 🎯 Overview

Goalcast is a football data aggregation and analysis toolkit that provides:

- **Multi-provider data sources**: FootyStats, Sportmonks, and more
- **MCP Server**: Seamless integration with AI assistants for football data queries
- **Layered architecture**: Clean datasource abstraction with caching
- **Async-first design**: High-performance concurrent data fetching
- **Docker support**: Easy deployment to any environment

## 📦 Installation

### Local Development

```bash
# Clone the repository
git clone https://github.com/skyold/Goalcast.git
cd Goalcast

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Docker Deployment

```bash
# Build and run
docker build -t goalcast-mcp .
docker-compose up -d
```

## 🔧 Configuration

### 1. Set up API Keys

Copy the environment template and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# Data Sources
FOOTYSTATS_API_KEY=your_footystats_api_key_here
SPORTMONKS_API_KEY=your_sportmonks_api_key_here

# AI Analysis (optional)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 2. Configure MCP Client

Copy the MCP configuration template:

```bash
cp mcporter.json.example mcporter.json
```

For different deployment scenarios, see [MCP Migration Guide](docs/MCP_MIGRATION_GUIDE.md).

## 🚀 Usage

### As MCP Server

The primary use case is as an MCP server for AI assistants:

```bash
# Local development mode
python mcp_server/server.py

# Or use the deployment script
./scripts/deploy_mcp.sh local
```

**Available MCP Tools**:

#### FootyStats Provider
- `footystats_get_league_list` - Get available leagues
- `footystats_get_todays_matches` - Get today's matches
- `footystats_get_league_matches` - Get league match schedule
- `footystats_get_league_tables` - Get league standings
- `footystats_get_league_stats` - Get detailed league statistics
- `footystats_get_match_details` - Get match details with H2H
- `footystats_get_team_details` - Get team statistics
- `footystats_get_btts_stats` - Get BTTS (Both Teams To Score) stats
- `footystats_get_over25_stats` - Get Over 2.5 Goals stats

#### Sportmonks Provider
- `sportmonks_get_livescores` - Get live scores
- `sportmonks_get_fixtures_by_date` - Get fixtures by date
- `sportmonks_get_standings` - Get league standings
- `sportmonks_get_lineups` - Get match lineups
- `sportmonks_get_player_stats` - Get player statistics
- `sportmonks_get_odds_movement` - Get odds data
- `sportmonks_get_head_to_head` - Get H2H records

### Data Management

Save API responses to local files:

```python
from utils.data_manager import save_json_data, load_json_data

# Save data
data = await provider.get_todays_matches()
save_json_data(data, "todays_matches")
# Saves to: data/todays_matches.json

# Load data
data = load_json_data("todays_matches")
```

See [Data Directory Guide](data/README.md) for details.

## 📁 Project Structure

```
Goalcast/
├── config/              # Configuration management
│   └── settings.py
├── data/                # Data files (auto-generated, git-ignored)
│   ├── README.md
│   └── *.json
├── docs/                # Documentation
│   ├── README.md
│   ├── MCP_CONFIG_GUIDE.md
│   ├── MCP_MIGRATION_GUIDE.md
│   └── DATA_DIRECTORY_SETUP.md
├── mcp_server/          # MCP server implementation
│   └── server.py
├── provider/            # Data providers
│   ├── footystats/
│   │   ├── client.py
│   │   └── README.md
│   ├── sportmonks/
│   │   └── client.py
│   └── base.py
├── scripts/             # Utility scripts
│   ├── deploy_mcp.sh
│   └── save_data_example.py
├── utils/               # Utility modules
│   ├── data_manager.py
│   ├── cache.py
│   └── logger.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── requirements.txt
```

## 🛠️ Development

### Deployment Scripts

Use the automated deployment script:

```bash
# Check current configuration
./scripts/deploy_mcp.sh check

# Local development setup
./scripts/deploy_mcp.sh local

# Docker deployment
./scripts/deploy_mcp.sh docker

# Remote server setup
./scripts/deploy_mcp.sh remote
```

### Running Tests

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=goalcast --cov-report=html
```

## 📚 Documentation

- **[MCP Configuration Guide](docs/MCP_CONFIG_GUIDE.md)** - Detailed MCP server configuration
- **[MCP Migration Guide](docs/MCP_MIGRATION_GUIDE.md)** - Migration and deployment guide
- **[Data Directory Setup](docs/DATA_DIRECTORY_SETUP.md)** - Data management guide
- **[Data Directory README](data/README.md)** - Using the data management utilities
- **[FootyStats Provider](provider/footystats/README.md)** - FootyStats API usage

## 🌐 Deployment Options

### 1. Local Development
- Uses relative paths
- Runs directly from source
- Best for development and testing

### 2. Docker Container
- Fully isolated environment
- Production-ready
- Easy to scale

```bash
docker-compose up -d
```

### 3. Remote Server
- SSE (Server-Sent Events) transport
- Connect from anywhere
- Suitable for team collaboration

See [MCP Migration Guide](docs/MCP_MIGRATION_GUIDE.md) for detailed instructions.

## 🔑 API Rate Limits

| Provider | Rate Limit | Notes |
|----------|-----------|-------|
| FootyStats | 1800 requests/hour | Resets hourly |
| Sportmonks | Varies by plan | Check your plan |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Data provided by [FootyStats](https://footystats.org/api)
- Data provided by [Sportmonks](https://www.sportmonks.com/)
- Built with [FastMCP](https://modelcontextprotocol.io/)

## 📞 Support

- Open an issue on [GitHub](https://github.com/skyold/Goalcast/issues)
- Check the [documentation](docs/)
- Review existing [examples](scripts/)
