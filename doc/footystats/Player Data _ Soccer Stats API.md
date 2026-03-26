# Player Data

# Player - Individual
Individual Player Endpoint. Provides stats for the player on a per season/league basis.

## Get Player
`GET` `https://api.football-data-api.com/player-stats?key=YOURKEY&player_id=*` Returns an array of player stats across all seasons and leagues that they've played in.
#### Query Parameters

| key* | string | Your API Key |
| --- | --- | --- |
| key* | string | Your API Key |
| player_id* | integer | ID of the player that you would like to retrieve. Often obtained via League Players endpoint. |

```json
{
    "success": true,
    "data": [
        {
            "id": "3171",
            "competition_id": "6",
            "full_name": "Cristiano Ronaldo dos Santos Aveiro",
            "first_name": "Cristiano Ronaldo",
            "last_name": "dos Santos Aveiro",
            "known_as": "Cristiano Ronaldo",
            "shorthand": "cristiano-ronaldo",
            "age": "33",
            "league": "UEFA Champions League",
            "league_type": "Cup",
            "season": "2016/2017",
            "starting_year": "2016",
            "ending_year": "2017",
            "national_team_id": "0",
            "url": "/players/portugal/cristiano-ronaldo",
            "club_team_id": "84",
            "club_team_2_id": "-1",
            "position": "Forward",
            "minutes_played_overall": "1170",
            "minutes_played_home": "540",
            "minutes_played_away": "630",
            "birthday": "476438400",
            "nationality": "Portugal",
            "continent": "eu"
        }
    ]
}
```

### Queries and Parameters

> ℹ️ You can test this API call by using the key "example" and loading the matches from the English Premier League 2018/2019 season (ID: 1625).

| id | ID of the Player. |
| --- | --- |
| id | ID of the Player. |
| competition_id | ID of the season (and League) that the stats are based out of. |
| full_name / first_name / last_name | Name of the player. |
| known_as | Common name of the player. |
| shorthand | Programming friendly representation of the player's full name. |
| age | Current age. |
| league | Name of the league. |
| league_type | Type of the league. |
| season | Season year of the league. |
| starting_year / ending_year | Starting / Ending year of the league. |
| url | FootyStats URL of the player. |
| club_team_id | Team ID of the club that the player was in during this season. |
| club_team_2_id | Team ID of the club that the player has transferred to during this season. |
| position | Position of the player. |
| minutes_played_overall / home / away | Minutes played in this league this season. |
| birthday | UNIX representation of the player birthday. |
| nationality | Nationality of the player. |
| continent | Continent from which the player is from. |
| appearances_overall / home / away | Number of matches played. |
| goals_overall / home / away | Number of goals scored. |
| clean_sheets_overall / home / away | Number of clean sheets for this player's team for the matches that they played in. |
| conceded_overall / home / away | Number of goals conceded while the player was on the pitch. |
| assists_overall / home / away | Number of assists this player has earned. |
| penalty_goals | Number of goals scored via Penalty kick. |
| goals_involved_per_90_overall | Goals involved (Goals + Assists) per 90 minutes. |
| assists_per_90_overall | Assists per 90 minutes. |
| goals_per_90_overall / home / away | Goals scored per 90 minutes. |
| conceded_per_90_overall | Goals conceded per 90 minutes. |
| min_per_conceded_overall | Minutes per goal conceded. |
| cards_overall | Number of Yellow / Red cards earned during this season in this league. |
| yellow_cards_overall | Number of Yellow cards earned during this season in this league. |
| red_cards_overall | Number of Red cards earned during this season in this league. |
| min_per_match | Average number of minutes this player has played per match. |
| min_per_card_overall | Minutes per card (Yellow / Red). |
| min_per_assist_overall | Minutes per assist. |
| cards_per_90_overall | Cards per 90 minutes. |
| last_match_timestamp | When the last match was played. |
| detailed / average_rating_overall | Average player rating across all games. |
| detailed / assists_per_game_overall | Average number of assists per game. |
| detailed / assists_per90_percentile_overall | Percentile ranking for assists per 90 minutes. |
| detailed / passes_per_90_overall | Average number of passes per 90 minutes. |
| detailed / passes_per_game_overall | Average number of passes per game. |
| detailed / passes_per90_percentile_overall | Percentile ranking for passes per 90 minutes. |
| detailed / passes_total_overall | Total number of passes made during the season. |
| detailed / passes_completed_per_game_overall | Average number of completed passes per game. |
| detailed / passes_completed_total_overall | Total number of completed passes during the season. |
| detailed / pass_completion_rate_percentile_overall | Percentile ranking for pass completion rate. |
| detailed / passes_completed_per_90_overall | Completed passes per 90 minutes on average. |
| detailed / passes_completed_per90_percentile_overall | Percentile ranking for completed passes per 90 minutes. |
| detailed / short_passes_per_game_overall | Average number of short passes per game. |
| detailed / long_passes_per_game_overall | Average number of long passes per game. |
| detailed / key_passes_per_game_overall | Average number of passes that directly lead to a shot on goal per game. |
| detailed / key_passes_total_overall | Total of passes that directly lead to a shot on goal during the season. |
| detailed / crosses_per_game_overall | Average number of crosses per game. |
| detailed / tackles_per_90_overall | Tackles made per 90 minutes on average. |
| detailed / tackles_per_game_overall | Average number of tackles per game. |
| detailed / tackles_total_overall | Total number of tackles made during the season. |
| detailed / tackles_successful_per_game_overall | Average number of successful tackles per game. |
| detailed / dispossesed_per_game_overall | Average times the player was dispossessed per game. |
| detailed / saves_per_game_overall | Average number of saves per game (goalkeepers). |
| detailed / interceptions_per_game_overall | Average number of interceptions per game. |
| detailed / dribbles_successful_per_game_overall | Average number of successful dribbles per game. |
| detailed / shots_faced_per_game_overall | Average number of shots faced by the player’s team per game. |
| detailed / shots_per_goal_scored_overall | Average number of shots taken for each goal scored by the player’s team. |
| detailed / shots_per_90_overall | Average number of shots taken by the player per 90 minutes played. |
| detailed / shots_off_target_per_game_overall | Average number of shots off target by the player’s team per game. |
| detailed / dribbles_per_game_overall | Average number of dribbles made by the player per game. |
| detailed / shots_on_target_per_game_overall | Average number of shots on target by the player’s team per game. |
| detailed / xg_per_game_overall | Average expected goals per game for the player’s team. |
| detailed / aerial_duels_won_per_game_overall | Average number of aerial duels won by the player per game. |
| detailed / shots_total_overall | Total number of shots taken by the player’s team across all matches. |
| detailed / shots_per_game_overall | Average number of shots taken by the player per game. |
| detailed / shots_per90_percentile_overall | Percentile rank for the player’s shots per 90 minutes compared to others. |
| detailed / shots_on_target_total_overall | Total number of shots on target by the player’s team across all matches. |
| detailed / shots_on_target_per_90_overall | Average number of shots on target by the player’s team per 90 minutes played. |
| detailed / shots_on_target_per90_percentile_overall | Percentile rank for the player’s shots on target per 90 minutes compared to others. |
| detailed / shots_off_target_total_overall | Total number of shots off target by the player’s team across all matches. |
| detailed / shots_off_target_per_90_overall | Average number of shots off target by the player’s team per 90 minutes played. |
| detailed / shots_off_target_per90_percentile_overall | Percentile rank for the player’s shots off target per 90 minutes compared to others. |
| detailed / games_subbed_out | Total number of games where the player was substituted out. |
| detailed / games_subbed_in | Total number of games where the player was substituted in. |
| detailed / games_started | Total number of games where the player started the match. |
| detailed / tackles_per90_percentile_overall | Percentile rank for the player’s tackles per 90 minutes compared to others. |
| detailed / tackles_successful_per_90_overall | Average number of successful tackles made by the player per 90 minutes played. |
| detailed / tackles_successful_per90_percentile_overall | Percentile rank for the player’s successful tackles per 90 minutes compared to others. |
| detailed / tackles_successful_total_overall | Total number of successful tackles made by the player’s team across all matches. |
| detailed / interceptions_total_overall | Total number of interceptions made by the player’s team across all matches. |
| detailed / interceptions_per_90_overall | Average number of interceptions made by the player per 90 minutes played. |
| detailed / interceptions_per90_percentile_overall | Percentile rank for the player’s interceptions per 90 minutes compared to others. |
| detailed / crosses_total_overall | Total number of crosses attempted by the player’s team across all matches. |
| detailed / cross_completion_rate_percentile_overall | Percentile rank for the player’s cross completion rate compared to others. |
| detailed / crosses_per_90_overall | Average number of crosses attempted by the player per 90 minutes played. |
| detailed / crosses_per90_percentile_overall | Percentile rank for the player’s crosses per 90 minutes compared to others. |
| detailed / key_passes_per_90_overall | Average number of key passes made by the player per 90 minutes played. |
| detailed / key_passes_per90_percentile_overall | Percentile rank for the player’s key passes per 90 minutes compared to others. |
| detailed / dribbles_total_overall | Total number of dribbles made by the player’s team across all matches. |
| detailed / dribbles_per_90_overall | Average number of dribbles made by the player per 90 minutes played. |
| detailed / dribbles_per90_percentile_overall | Percentile rank for the player’s dribbles per 90 minutes compared to others. |
| detailed / dribbles_successful_total_overall | Total number of successful dribbles made by the player’s team across all matches. |
| detailed / dribbles_successful_per_90_overall | Average number of successful dribbles made by the player per 90 minutes played. |
| detailed / dribbles_successful_percentage_overall | Percentage of successful dribbles made by the player’s team across all matches. |
| detailed / saves_total_overall | Total number of saves made by the player across all matches. |
| detailed / save_percentage_percentile_overall | Percentile rank for the player’s save percentage compared to others. |
| detailed / saves_per_90_overall | Average number of saves made by the player per 90 minutes played. |
| detailed / saves_per90_percentile_overall | Percentile rank for the player’s saves per 90 minutes compared to others. |
| detailed / shots_faced_total_overall | Total number of shots faced by the player’s team across all matches. |
| detailed / shots_per_goal_conceded_overall | Average number of shots faced for each goal conceded by the player’s team. |
| detailed / conceded_per90_percentile_overall | Percentile rank for the player’s goals conceded per 90 minutes compared to others. |
| detailed / shots_faced_per_90_overall | Average number of shots faced by the player’s team per 90 minutes played. |
| detailed / shots_faced_per90_percentile_overall | Percentile rank for the player’s shots faced per 90 minutes compared to others. |
| detailed / save_percentage_overall | Save percentage for the player’s team across all matches. |
| detailed / xg_total_overall | Total expected goals accumulated by the player across all matches. |
| detailed / pass_completion_rate_overall | Percentage of completed passes out of total attempted by the player. |
| detailed / shot_accuraccy_percentage_overall | Percentage of shots on target out of total shots taken by the player. |
| detailed / shot_accuraccy_percentage_percentile_overall | Percentile rank of player’s shot accuracy compared to others. |
| detailed / dribbled_past_per90_percentile_overall | Percentile rank for times the player was dribbled past per 90 minutes. |
| detailed / dribbled_past_per_game_overall | Average number of times the player was dribbled past per game. |
| detailed / dribbled_past_per_90_overall | Average number of times the player was dribbled past per 90 minutes. |
| detailed / dribbled_past_total_overall | Total number of times the player was dribbled past across all matches. |
| detailed / dribbles_successful_per90_percentile_overall | Percentile rank for successful dribbles per 90 minutes by the player. |
| detailed / dribbles_successful_percentage_percentile_overall | Percentile rank for success rate of the player’s dribbles. |
| detailed / pen_scored_total_overall | Total number of penalties scored by the player. |
| detailed / pen_missed_total_overall | Total number of penalties missed by the player. |
| detailed / inside_box_saves_total_overall | Total number of saves made on shots from inside the box. |
| detailed / blocks_per_game_overall | Average number of blocks made per game by the player. |
| detailed / blocks_per_90_overall | Average number of blocks made by the player per 90 minutes. |
| detailed / blocks_total_overall | Total number of blocks made by the player across all matches. |
| detailed / blocks_per90_percentile_overall | Percentile rank for blocks per 90 minutes made by the player. |
| detailed / ratings_total_overall | Total number of match ratings recorded for the player. |
| detailed / clearances_per_game_overall | Average number of clearances made by the player per game. |
| detailed / clearances_per_90_overall | Average number of clearances made by the player per 90 minutes. |
| detailed / clearances_total_overall | Total number of clearances made by the player across all matches. |
| detailed / pen_committed_total_overall | Total number of penalties conceded by the player. |
| detailed / pen_save_percentage_overall | Percentage of penalties saved by the goalkeeper. |
| detailed / pen_committed_per_90_overall | Average number of penalties conceded by the player per 90 minutes. |
| detailed / pen_committed_per90_percentile_overall | Percentile rank for penalties conceded per 90 minutes. |
| detailed / pen_committed_per_game_overall | Average number of penalties conceded by the player per game. |
| detailed / pens_saved_total_overall | Total number of penalties saved by the goalkeeper. |
| detailed / pens_taken_total_overall | Total number of penalties taken by the player. |
| detailed / hit_woodwork_total_overall | Total number of times the player hit the woodwork with a shot. |
| detailed / hit_woodwork_per_game_overall | Average number of woodwork hits per game by the player. |
| detailed / hit_woodwork_per_90_overall | Average number of woodwork hits by the player per 90 minutes. |
| detailed / punches_total_overall | Total number of times the goalkeeper punched the ball clear. |
| detailed / punches_per_game_overall | Average number of punches per game made by the goalkeeper. |
| detailed / punches_per_90_overall | Average number of punches made by the goalkeeper per 90 minutes. |
| detailed / offsides_per_90_overall | Average number of offsides committed by the player per 90 minutes. |
| detailed / offsides_per_game_overall | Average number of offsides committed by the player per game. |
| detailed / offsides_total_overall | Total number of offsides committed by the player. |
| detailed / penalties_won_total_overall | Total number of penalties won by the player. |
| detailed / shot_conversion_rate_overall | Percentage of goals scored from total shots taken by the player. |
| detailed / shot_conversion_rate_percentile_overall | Percentile rank for player’s shot conversion rate. |
| detailed / minutes_played_percentile_overall | Percentile rank for total minutes played by the player. |
| detailed / matches_played_percentile_overall | Percentile rank for total matches played by the player. |
| detailed / min_per_goal_percentile_overall | Percentile rank for minutes per goal scored by the player. |
| detailed / min_per_conceded_percentile_overall | Percentile rank for minutes per goal conceded (goalkeeper or defender). |
| detailed / xa_total_overall | Total expected assists (xA) generated by the player. |
| detailed / xa_per90_percentile_overall | Percentile rank for expected assists per 90 minutes. |
| detailed / xa_per_game_overall | Average expected assists generated by the player per game. |
| detailed / xa_per_90_overall | Average expected assists generated by the player per 90 minutes. |
| detailed / npxg_total_overall | Total non-penalty expected goals (npxG) generated by the player. |
| detailed / npxg_per90_percentile_overall | Percentile rank for non-penalty expected goals (npxG) per 90 minutes. |
| detailed / npxg_per_game_overall | Average non-penalty expected goals generated by the player per game. |
| detailed / npxg_per_90_overall | Average non-penalty expected goals generated by the player per 90 minutes. |
| detailed / club_team_2_id | Secondary club ID associated with the player (e.g. loan or B team). |
| detailed / club_team_id | Primary club ID associated with the player. |
| detailed / fouls_drawn_per90_percentile_overall | Percentile rank for fouls drawn by the player per 90 minutes. |
| detailed / fouls_drawn_total_overall | Total number of fouls drawn by the player. |
| detailed / fouls_drawn_per_game_overall | Average number of fouls drawn by the player per game. |
| detailed / fouls_drawn_per_90_overall | Average number of fouls drawn by the player per 90 minutes. |
| detailed / fouls_committed_per_90_overall | Average number of fouls committed by the player per 90 minutes. |
| detailed / fouls_committed_per_game_overall | Average number of fouls committed by the player per game. |
| detailed / fouls_committed_per90_percentile_overall | Percentile rank for fouls committed by the player per 90 minutes. |
| detailed / fouls_committed_total_overall | Total number of fouls committed by the player. |
| detailed / xg_per_90_overall | Average expected goals (xG) generated by the player per 90 minutes. |
| detailed / xg_per90_percentile_overall | Percentile rank for expected goals (xG) per 90 minutes. |
| detailed / average_rating_percentile_overall | Percentile rank for the player's average match rating. |
| detailed / clearances_per90_percentile_overall | Percentile rank for clearances made per 90 minutes. |
| detailed / hit_woodwork_per90_percentile_overall | Percentile rank for woodwork hits per 90 minutes. |
| detailed / punches_per90_percentile_overall | Percentile rank for goalkeeper punches per 90 minutes. |
| detailed / offsides_per90_percentile_overall | Percentile rank for offsides committed per 90 minutes. |
| detailed / aerial_duels_won_per90_percentile_overall | Percentile rank for aerial duels won per 90 minutes. |
| detailed / aerial_duels_won_total_overall | Total number of aerial duels won by the player. |
| detailed / aerial_duels_won_percentage_overall | Percentage of aerial duels won by the player. |
| detailed / aerial_duels_won_per_90_overall | Average number of aerial duels won by the player per 90 minutes. |
| detailed / duels_per_90_overall | Average number of total duels contested by the player per 90 minutes. |
| detailed / duels_per_game_overall | Average number of duels the player engaged in per game. |
| detailed / duels_total_overall | Total number of duels the player engaged in across all matches. |
| detailed / duels_won_total_overall | Total number of duels the player won across all matches. |
| detailed / duels_won_per90_percentile_overall | Percentile ranking of the player's duels won per 90 minutes compared to peers. |
| detailed / duels_per90_percentile_overall | Percentile ranking of the player's duels per 90 minutes compared to peers. |
| detailed / duels_won_per_90_overall | Average number of duels the player won per 90 minutes. |
| detailed / duels_won_per_game_overall | Average number of duels the player won per game. |
| detailed / duels_won_percentage_overall | Percentage of total duels won by the player. |
| detailed / dispossesed_total_overall | Total number of times the player lost possession when challenged. |
| detailed / dispossesed_per_90_overall | Average number of times the player was dispossessed per 90 minutes. |
| detailed / dispossesed_per90_percentile_overall | Percentile ranking of the player's dispossessions per 90 minutes compared to peers. |
| detailed / progressive_passes_total_overall | Total number of passes made by the player that moved the ball significantly forward. |
| detailed / cross_completion_rate_overall | Percentage of successful crosses delivered by the player. |
| detailed / accurate_crosses_total_overall | Total number of accurate crosses delivered by the player. |
| detailed / accurate_crosses_per_game_overall | Average number of accurate crosses per game. |
| detailed / accurate_crosses_per_90_overall | Average number of accurate crosses per 90 minutes. |
| detailed / accurate_crosses_per90_percentile_overall | Percentile ranking of accurate crosses per 90 minutes compared to peers. |
| detailed / games_started_percentile_overall | Percentile ranking for the proportion of games the player started. |
| detailed / games_subbed_in_percentile_overall | Percentile ranking for the frequency the player was substituted into games. |
| detailed / games_subbed_out_percentile_overall | Percentile ranking for the frequency the player was substituted out of games. |
| detailed / hattricks_total_overall | Total number of hat-tricks (three goals in a single match) scored by the player. |
| detailed / two_goals_in_a_game_total_overall | Total number of matches where the player scored two goals. |
| detailed / three_goals_in_a_game_total_overall | Total number of matches where the player scored three goals. |
| detailed / two_goals_in_a_game_percentage_overall | Percentage of matches where the player scored two goals. |
| detailed / three_goals_in_a_game_percentage_overall | Percentage of matches where the player scored three goals. |
| detailed / goals_involved_per90_percentile_overall | Percentile ranking for goals + assists per 90 minutes compared to peers. |
| detailed / goals_per90_percentile_overall | Percentile ranking for goals scored per 90 minutes overall. |
| detailed / goals_per90_percentile_away | Percentile ranking for goals scored per 90 minutes in away matches. |
| detailed / goals_per90_percentile_home | Percentile ranking for goals scored per 90 minutes in home matches. |
| detailed / annual_salary_eur | Player's annual salary in euros. |
| detailed / annual_salary_eur_percentile | Percentile ranking of the player's annual salary compared to peers. |
| detailed / clean_sheets_percentage_percentile_overall | Percentile ranking of the percentage of matches with clean sheets by player's team. |
| detailed / min_per_card_percentile_overall | Percentile ranking for average minutes played per card received. |
| detailed / cards_per90_percentile_overall | Percentile ranking for number of cards received per 90 minutes. |
| detailed / booked_over05_overall | Total number of matches where the player received more than 0.5 cards. |
| detailed / booked_over05_percentage_overall | Percentage of matches where the player received more than 0.5 cards. |
| detailed / booked_over05_percentage_percentile_overall | Percentile ranking for percentage of games with more than 0.5 cards received. |
| detailed / shirt_number9 | Indicates whether the player wears the shirt number 9. |
| detailed / detailed_minutes_played_recorded_overall | Total minutes played by the player in matches with full data coverage. |
| detailed / detailed_matches_played_recorded_overall | Total number of matches played by the player with full data coverage. |

[PreviousLeague Table](https://footystats.org/api/documentations/league-table) [NextReferee - Individual](https://footystats.org/api/documentations/referee-individual)