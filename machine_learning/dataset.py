from dubito.game_data import honest_times, dishonest_times, doubts_count, turns_count


class DubitoDataset:
    def __init__(self) -> None:
        self.who = []
        self.data = []

    def add_data(self, hand: list, who: str, input_player, output_player) -> None:
        prev_id = input_player.prev_player_id
        next_id = input_player.next_player_id
        h = input_player.history

        data_list = [
            hand,
            input_player.board_cards,
            input_player.playing_cards,
            input_player.current_number,
            input_player.n_cards_played,
            input_player.streak,
            # prev player stats (derived from history)
            turns_count(prev_id, h),
            doubts_count(prev_id, h),
            honest_times(prev_id, h),
            dishonest_times(prev_id, h),
            input_player.player_card_counts.get(prev_id, 0),
            # next player stats (derived from history)
            turns_count(next_id, h),
            doubts_count(next_id, h),
            honest_times(next_id, h),
            dishonest_times(next_id, h),
            input_player.player_card_counts.get(next_id, 0),
            # output
            output_player.doubt,
            output_player.number,
            output_player.cards,
            -1,  # result placeholder
        ]

        self.data.append(data_list)
        self.who.append(who)

    def add_result(self, winners: list, losers: list) -> None:
        winner_ids = [w.id for w in winners]
        for pl, dt in zip(self.who, self.data):
            dt[-1] = 1 if pl in winner_ids else 0

    def get_dataset(self) -> list:
        return self.data
