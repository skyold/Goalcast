from goalcast.provider.base import BaseProvider
from goalcast.provider.footystats.client import FootyStatsProvider
from goalcast.provider.sportmonks.client import SportmonksProvider
from goalcast.provider.football_data.client import FootballDataProvider
from goalcast.provider.understat.client import UnderstatProvider
from goalcast.provider.clubelo.client import ClubEloProvider
from goalcast.provider.odds.client import OddsProvider
from goalcast.provider.weather.client import WeatherProvider
from goalcast.provider.transfermarkt.client import TransfermarktProvider
from goalcast.provider.espn.client import ESPNProvider

FootyStatsClient = FootyStatsProvider
SportmonksClient = SportmonksProvider
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
    "SportmonksProvider",
    "FootballDataProvider",
    "UnderstatProvider",
    "ClubEloProvider",
    "OddsProvider",
    "WeatherProvider",
    "TransfermarktProvider",
    "ESPNProvider",
    "FootyStatsClient",
    "SportmonksClient",
    "FootballDataClient",
    "UnderstatClient",
    "ClubEloClient",
    "OddsAPIClient",
    "WeatherClient",
    "TransfermarktClient",
    "ESPNClient",
]
