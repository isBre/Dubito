 
# Introduzione
L'obiettivo di questo progetto è stato quello di determinare l'IA più abile per giocare a Dubito. All'interno di questo lavoro, scoprirete sia il gioco stesso che il quadro di riferimento per condurre numerosi esperimenti che coinvolgono diverse IA.
# Il gioco
**Dubito** è un gioco di carte dinamico progettato per 3-8 giocatori. Per dare il via al gioco, le carte vengono distribuite in modo circolare, a partire dal giocatore che inizia. 
A ogni turno, i giocatori hanno la possibilità di fare una giocata o di dubitare della mossa del giocatore precedente. Se non ci sono carte sul tavolo, i giocatori si limitano a fare una giocata. Quando si effettua una giocata, un giocatore può scegliere di mettere 1-3 carte a faccia in giù e dichiarare un numero (da 1 a Re). Una giocata veritiera si verifica quando il numero dichiarato corrisponde alle carte piazzate (ad esempio, dichiarando "1" e piazzando due carte di valore 1), mentre qualsiasi altra dichiarazione costituisce un bluff.
In alternativa, i giocatori possono scegliere di dubitare della dichiarazione del giocatore precedente. Se il giocatore precedente stava effettivamente bluffando, raccoglie tutte le carte sul tavolo e il giocatore che dubita procede con il proprio turno. Al contrario, se il giocatore precedente era sincero, il giocatore in dubbio raccoglie tutte le carte sul tavolo e il gioco continua con il giocatore successivo.
Il gioco culmina quando rimangono solo due giocatori, con la conseguente eliminazione di questi ultimi e la vittoria dei restanti partecipanti.

# Per ridurre la complessità degli esperimenti, sono state implementate alcune semplificazioni: 
- **Numero di vincitori**: Limitato a un solo vincitore, poiché gli scenari con più vincitori in una singola partita sono trattati come istanze ricorsive del "caso di un vincitore". 
- **Nessun Jolly**: Per ridurre la complessità dell'IA. 

# AI
L'AI comprende una semplice struttura ad albero che delinea i vari scenari di Dubito in base alle informazioni fornite. 

![Dubito Tree AI](imgs\dubito.png) 

## Input 

Per consentire un processo decisionale ben informato, a ogni turno l'IA riceve un dizionario. Questo dizionario contiene le seguenti informazioni:

- **mie_carte**: Lista di interi, rappresenta le carte del giocatore corrente 
- **carte_a_terra**: numero compreso tra 0 ed N, rappresenta il numero di carte a terra (0 significa che si è il primo) 
- **numeri_disponibili**: Lista di valori (inizialmente rappresenta una lista di valori da 1 a 13), rappresenta la lista di tutti i numeri senza i numeri che sono stati scartati 
- **numero_corrente**: intero compreso tra 1 e 13, rappresenta il numero di carte chiamato dal giocatore precedente (0 significa che si è il primo) 
- **n_carte_giocate**: numero compreso tra 1 ed N, rappresenta il numero di carte giocate dal giocatore precedente 
- **streak** : numero compreso tra 0 ed N, rappresenta il numero di turni senza dubito 
- **prec_n_cards**: intero compreso tra 0 ed N, rappresenta la quantità di carte del giocatore precedente
- **prec_turns**: intero compreso tra 1 ed N, rappresenta quanti turni ha giocato il giocatore precedente 
- **prec_not_first_turns**: intero compreso tra 1 ed N, rappresenta quanti turni ha giocato il giocatore precedente (non di prima mano) 
- **prec_doubts**: intero compreso tra 0 ed N, rappresenta il numero di volte in cui il giocatore precedente ha dubitato 
- **prec_honest_times**: intero compreso tra 0 ed N, rappresenta il numero di volte in cui il giocatore precedente è stato onesto in caso di dubito 
- **prec_dishonest_times**: intero compreso tra 0 ed N, rappresenta il numero di volte in cui il giocatore precedente è stato disonesto in caso di dubito
- **succ_n_cards**: intero compreso tra 0 ed N, rappresenta la quantità di carte del giocatore successivo
- **succ_turns**: intero compreso tra 1 ed N, rappresenta quanti turni ha giocato il giocatore successivo 
- **succ_not_first_turns**: intero compreso tra 1 ed N, rappresenta quanti turni ha giocato il giocatore successivo (non di prima mano) 
- **succ_doubts**: intero compreso tra 0 ed N, rappresenta il numero di volte in cui il giocatore successivo ha dubitato 
- **succ_honest_times**: intero compreso tra 0 ed N, rappresenta il numero di volte in cui il giocatore successivo è stato onesto in caso di dubito 
- **succ_dishonest_times**: intero compreso tra 0 ed N, rappresenta il numero di volte in cui il giocatore successivo è stato disonesto in caso di dubito  