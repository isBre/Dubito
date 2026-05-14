from typing import List, Dict, Tuple

class DubitoDataset:
    def __init__(self) -> None:
        self.who = []
        self.data = []
    
    def add_data(self, hand: List, who: str, input_player, output_player: Dict) -> None:
        in_keys = ['board_cards', 'playing_cards', 'current_number', 'n_cards_played', 'streak']
        pl_keys = ['turns', 'not_first_turns', 'doubts', 'honest_times', 'dishonest_times', 'n_cards']
        ou_keys = ['doubt', 'cards', 'number']
        data_list = []
        data_list.append(hand)
        data_list.extend([getattr(input_player, k) for k in in_keys])
        data_list.extend([getattr(input_player.prev, k) for k in pl_keys])
        data_list.extend([getattr(input_player.next, k) for k in pl_keys])
        data_list.extend([output_player[k] for k in ou_keys])
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