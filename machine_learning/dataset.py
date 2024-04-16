from typing import List, Dict, Tuple

class DubitoDataset:
    def __init__(self) -> None:
        self.who = []
        self.data = []
    
    def add_data(self, hand: List, who: str, input_player : Dict, output_player : Dict) -> None:
        in_keys_to_append = ['board_cards', 'playing_cards', 'current_number', 'n_cards_played', 'streak']
        pl_keys = ['turns', 'not_first_turns', 'doubts', 'honest_times', 'dishonest_times', 'n_cards']
        ou_keys_to_append = ['doubt', 'cards', 'number']
        data_list = []
        data_list.append(hand)
        for key in in_keys_to_append:
            data_list.append(input_player[key])
        data_list.extend([input_player['prev'][key] for key in pl_keys])
        data_list.extend([input_player['next'][key] for key in pl_keys])
        for key in ou_keys_to_append:
            data_list.append(output_player[key])
        data_list.append(-1)
        
        self.data.append(data_list)
        self.who.append(who)
    
    def add_result(self, winners : List, losers : List) -> None:
        winners = [w.id for w in winners]
        for pl, dt in zip(self.who, self.data):
            if pl in winners:
                dt[-1] = 1
            else:
                dt[-1] = 0
    
    def get_dataset(self) -> Tuple[List, List]:
        return self.data