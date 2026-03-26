from provider.base import BaseProvider
from provider.footystats.client import FootyStatsProvider
from provider.football_data.client import FootballDataProvider
from provider.understat.client import UnderstatProvider
from provider.clubelo.client import ClubEloProvider
from provider.odds.client import OddsProvider
from provider.weather.client import WeatherProvider
from provider.transfermarkt.client import TransfermarktProvider
from provider.espn.client import ESPNProvider

FootyStatsClient = FootyStatsProvider
FootballDataClient = FootballDataProvider
UnderstatClient = UnderstatProvider
ClubEloClient = ClubEloProvider
OddsAPIClient = OddsProvider
WeatherClient = WeatherProvider
TransfermarktClient = TransfermarktProvider
ESPNClient = ESPNProvider

__all__ = [
    "BaseProvider",
    "FootyStatsProvider",
    "FootballDataProvider",
    "UnderstatProvider",
    "ClubEloProvider",
    "OddsProvider",
    "WeatherProvider",
    "TransfermarktProvider",
    "ESPNProvider",
    "FootyStatsClient",
    "FootballDataClient",
    "UnderstatClient",
    "ClubEloClient",
    "OddsAPIClient",
    "WeatherClient",
    "TransfermarktClient",
    "ESPNClient",
]
