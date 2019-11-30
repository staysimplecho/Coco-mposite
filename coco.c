// Assignment 1 19T1 COMP1511 Coco
//
// This program was written by Sijia Hao (z5141464)
// on 20/03/2019
//

#include <stdio.h>
#include <assert.h>


#define ACTION_PLAYER_NAME    0
#define ACTION_DISCARD        1
#define ACTION_PLAY_CARD      2

#define N_CARDS              40
#define N_CARDS_INITIAL_HAND 10
#define N_PLAYERS             4
#define N_CARDS_DISCARDED     3

#define CARD_MIN             10
#define CARD_MAX             49


// IF YOU NEED MORE #defines ADD THEM HERE
#define YES                  1
#define NOT_FOUND            -1
#define DOUGLAS              42
#define CARD_NUM             50
#define N_PRIMES             11
#define P_LEAST_COMM_DIVS    210 // 2*3*5*7

void print_player_name(void);
void choose_discards(void);
void choose_card_to_play(void);

// ADD PROTOTYPES FOR YOUR FUNCTIONS HERE
void read_into_array(int size, int array[]);
int do_i_have_douglas(int size, int mine[]);
int larger_than_douglas(int size, int array[]);
int second_largest(int array[]);
int was_prime_played(int size, int array[]);
int largest_anyway(int size, int array[]);
int find_elig_largest(int s_size, int target, int source[], int eligible[]);
int is_prime(int num);
int is_cocomposite(int first, int mine);
/*
void others_cards(int after1[], int after2[], int after3[], int n_all_prev, int all_prev[]);
int who_win_the_round(int *round_played);
*/

// You should not need to change this main function

int main(void) {

    int which_action = 0;
    scanf("%d", &which_action);
    if (which_action == ACTION_PLAYER_NAME) {
        print_player_name();
    } else if (which_action == ACTION_DISCARD) {
        choose_discards();
    } else if (which_action == ACTION_PLAY_CARD) {
        choose_card_to_play();
    }

    return 0;
}

void print_player_name(void) {

    printf("Keep It Player\n");

}

void choose_discards() {

    // read the cards in your hand
    int initial_cards[N_CARDS_INITIAL_HAND] = {0};
    int n_initial = N_CARDS_INITIAL_HAND;
    read_into_array(n_initial, initial_cards);

    // discard the largest three cards except DOUGLAS(if you have)
    int i = 1;
    int discard = 0;
    while (discard < N_CARDS_DISCARDED) {
        if (initial_cards[N_CARDS_INITIAL_HAND - i] != DOUGLAS) {
            printf("%d ", initial_cards[N_CARDS_INITIAL_HAND - i]);
            discard++;
        }     
        i++;
    }
    printf("\n");

}

void choose_card_to_play(void) {
    
    // # of cards in my hand
    // # of cards played this round
    // my table position
    int n_cards_in_hand, n_played_this_round, table_pos;
    scanf("%d %d %d", &n_cards_in_hand, &n_played_this_round, &table_pos);

    // cards in my hand
    int cards_in_hand[N_CARDS_INITIAL_HAND] = {0};
    read_into_array(n_cards_in_hand, cards_in_hand);
    
    // cards played this round
    int cards_played_this_round[N_PLAYERS] = {0};
    read_into_array(n_played_this_round, cards_played_this_round);

    // all cards played in previous rounds
    int all_prev_played[N_CARDS] = {0};
    int n_all_prev_played = (N_CARDS_INITIAL_HAND - n_cards_in_hand) * N_PLAYERS;
    read_into_array(n_all_prev_played, all_prev_played);

    // cards i discarded
    int discarded[N_CARDS_DISCARDED] = {0};
    int n_discarded = N_CARDS_DISCARDED;
    read_into_array(n_discarded, discarded);
    
    // cards i received
    int received[N_CARDS_DISCARDED] = {0};
    int n_received = N_CARDS_DISCARDED;
    read_into_array(n_received, received);
    

    // always play the LARGEST eligible card
    int all_eligible[N_CARDS] = {0};
    int largest = largest_anyway(n_cards_in_hand, cards_in_hand);
    
    // if you are the 1st player in round
    if (n_played_this_round == 0) {
        int prime_played = was_prime_played(n_all_prev_played, all_prev_played);
        // if prime was played before
        if (prime_played == YES) {
            if (largest == DOUGLAS) {
                printf("%d\n", second_largest(cards_in_hand));
            } else {
                printf("%d\n", largest);
            }
        } else {
        // if prime wasn't played before
            int lcd = P_LEAST_COMM_DIVS;
            int elig = find_elig_largest(n_cards_in_hand,
                       lcd, cards_in_hand, all_eligible);

            if (elig != NOT_FOUND && elig != DOUGLAS) {
                printf("%d\n", elig);        
            } else if (elig != NOT_FOUND && elig == DOUGLAS) {
                elig = second_largest(all_eligible);
                printf("%d\n", elig);
            } else {
                printf("%d\n", largest);
            }
        }
    } else {    
    // if you are the 2nd..4th player in round
        int elig = find_elig_largest(n_cards_in_hand,
                       cards_played_this_round[0], cards_in_hand, all_eligible);
        int dangerous = do_i_have_douglas(n_cards_in_hand, cards_in_hand);
        
        // when i have DOUGLAS 
        // and someone played a card larger than DOUGLAS
        if (dangerous != NOT_FOUND &&
            larger_than_douglas(n_played_this_round
                                , cards_played_this_round) == YES) {
            printf("42\n");
        } else if (dangerous != NOT_FOUND &&
                   larger_than_douglas(n_played_this_round
                                       , cards_played_this_round) != YES) {
        // when i have DOUGLAS 
        // but no one played a card larger than DOUGLAS
            if (elig != NOT_FOUND && elig != DOUGLAS) {
                printf("%d\n", elig);
            } else if (elig != NOT_FOUND && elig == DOUGLAS) {
                elig = second_largest(all_eligible);
                printf("%d\n", elig);
            } else {
                printf("%d\n", largest);
            }
        } else {
        // when i don't have DOUGLAS
            if (elig != NOT_FOUND) {
                printf("%d\n", elig);
            } else {
                printf("%d\n", largest);
            }
        }
    }

}

// ADD YOUR FUNCTIONS HERE

// read stdin inputs in an array
void read_into_array(int size, int array[]) {
    
    int i = 0;
    while (i < size) {
        scanf("%d", &array[i]);
        i++;
    }
    
}

// whether the Douglas is in my hand
// YES, return the index of DOUGLAS in my array of cards
// NO, return -1(NOT_FOUND);
int do_i_have_douglas(int size, int mine[]) {
    
    int i = size - 1;
    while (i >= 0) {
        if (mine[i] == DOUGLAS) {
            return i;
        }
        i--;
    }
    return NOT_FOUND;
    
}

// whether a card played in this round is larger than DOUGLAS
// YES, return 1(YES)
// NO, return -1(NOT_FOUND)
int larger_than_douglas(int size, int array[]) {
    
    int i = 0;
    int douglas = DOUGLAS;
    int coco_douglas = is_cocomposite(array[0], douglas);
    while (i < size) {
        if (array[i] > DOUGLAS && coco_douglas != NOT_FOUND) {
            return YES;
        }
        i++;
    }
    return NOT_FOUND;

}

// return the second largest eligible card
// when the largest is DOUGLAS
int second_largest(int array[]) {
    
    int i = 0;
    while (i < N_CARDS) {
        if (array[i] == DOUGLAS && i != 0) {
            return array[i - 1];
        }
        i++;
    }
    return DOUGLAS;
    
}

// whether a prime is played in previous rounds
// YES, return 1(YES)
// NO, return -1(NOT_FOUND)
int was_prime_played(int size, int array[]) {
    
    int i = 0;
    while (i < size) {
        if (is_prime(array[i]) == array[i]) {
            return YES;
        }
        i++;
    }
    return NOT_FOUND;
    
}

// find the largest number in an array
// and return its value
int largest_anyway(int size, int array[]) {
    
    int largest = array[0];
    int i = 1;
    while (i < size) {
        if (array[i] > largest) {
            largest = array[i];
        }
        i++;
    }
    return largest;
    
}

// find the largest coprime/coco card in hand and return its value
// if no card is eligible, return -1(NOT_FOUND)
int find_elig_largest(int s_size, int target, int source[], int eligible[]) {
    
    int s_i = 0;
    int e_i = 0;
    if (is_prime(target) == target) {
        while (s_i < s_size) {
            if (is_prime(source[s_i]) == source[s_i]) {
                eligible[e_i] = source[s_i];
                e_i++;
            }
            s_i++;
        }
    } else {
        while (s_i < s_size) {
            if (is_cocomposite(target, source[s_i]) == source[s_i]) {
                eligible[e_i] = source[s_i];
                e_i++;
            }
            s_i++;
        }
    }

    if (e_i == 0) {
        return NOT_FOUND;
    } else {    
        return eligible[e_i - 1];
    }
    
}

// whether a number is a prime in range 10~49
// YES, return that number
// NO, return -1(NOT_FOUND)
int is_prime(int num) {
    
    int all_primes[N_PRIMES] = {11, 13, 17, 19, 23, 29,
                                31, 37, 41, 43, 47};
    int i = 0;
    while (i < N_PRIMES) {
        if (num == all_primes[i]) {
            return num;
        }
        i++;
    }
    return NOT_FOUND;
    
}

// whether my card is cocomposite with a given number
// YES, return the value of my card
// NO, return -1(NOT FOUND)
int is_cocomposite(int first, int mine) {
    
    int high, low;
    if (mine >= first) {
        high = mine;
        low = first;
    } else {
        high = first;
        low = mine;
    }
    int i = 2;
    while (i < low) {
        if (low % i == 0 && high % i == 0) {
            return mine;
        }
        i++;
    }
    return NOT_FOUND;
    
}
