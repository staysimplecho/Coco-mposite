#!/usr/bin/python3 -B

import argparse, atexit, codecs, collections, copy, getpass, glob, io, os, random, re, shutil, signal, socket, subprocess, sys, time, tempfile, zipfile

ACTION_PLAYER_NAME   = 0
ACTION_DISCARD       = 1
ACTION_PLAY_CARD     = 2

N_CARDS_IN_HAND      = 10
N_PLAYERS            = 4
N_CARDS_DISCARDED    = 3

CARD_MIN             = 10
CARD_MAX             = 49

SPECIAL_CARD         = '42'
PRIME_PENALTY        = 1
SPECIAL_CARD_PENALTY = 7
ILLEGAL_PLAY_PENALTY = 5

CARDS = [n for n in range(CARD_MIN, CARD_MAX + 1)]

COCOMPOSITE_WITH = collections.OrderedDict((str(n), frozenset(str(m) for m in CARDS if [f for f in range(2, min(m, n)) if m % f == 0 and n % f == 0])) for n in CARDS)

# mlalias cs1511.19T1.tutors|grep '^ *z'|sed 's/.*z/z/'|xargs -i@ grep @ /home/teachadmin/lib/student_names|cut -d\| -f3|sed 's/.*, /"/;s/ .*//i;s/$/",/'|sort|uniq|tr -d '\n'
SYSTEM_PLAYER_NAMES = ["Alex","Andrew","Aydin","Benjamin","Braedon","Claire","Connor","Costa","David","Dean","Dylan","Eleni","Elizabeth","Emily","Finbar","Gal","George","Harrison","Heather","Jamal","Kane","Kangying","Livia","Marc","Matthew","Michael","Minh","Mitchell","Nathan","Nicholas","Oscar","Peter","Reede","Sabrina","Stephen","Trung","Vincent","Xue","Zachary"]


MAX_SUPPLIED_PLAYER_NAME_CHARS = 32

VERSION = "0.1"

def main(return_world=False):
    global args
    args = args_parser()
    post_process_args(args)
    random.seed(args.seed)
    default_player_names = random.sample(SYSTEM_PLAYER_NAMES, N_PLAYERS)
    players = [{
        'system' : True,
        'source' : 'system',
        'name' : default_player_names[player],
        'colored_name' : default_player_names[player],
        'get_play': random_player,
        'get_discards': random_discarder
        } for player in range(N_PLAYERS)]
    binaries = compile_players(args)
    for (player, binary, source) in zip(players, binaries, args.source_files):
         player['system'] = False
         player['binary'] = binary
         player['source'] = source
         player['name'] = run_binary_for_player_name(player).strip()
         player['get_discards'] = run_binary_for_discards
         player['get_play'] = run_binary_for_play
    if args.interactive_player:
        replace_player = 3 if binaries else 0
        players[replace_player].update({
             'name' : "You",
             'system' : False,
             'source' : 'interactive',
             'get_discards' : interactive_discarder,
             'get_play' : interactive_player,
        })
    sanitize_player_names(players)
    color_player_names(players)
    finishing_positions = play_game(players)
    if args.print_summary:
        print_summary(finishing_positions)
    exit_game()

def args_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--seed", type=int, default=random.getrandbits(24), help="random number generator seed")
    parser.add_argument("--compiler", default="dcc", help="compiler for C source files")
    parser.add_argument("--no_valgrind", action="store_false", dest="valgrind", default=True, help="don't also run binary with valgrind to check for uninitialized variables")

    parser.add_argument("--colorize", action="store_true", default=sys.stdout.isatty(), help="colorize output")
    parser.add_argument("--no_colorize", action="store_false", dest="colorize",  help="show test input")

    parser.add_argument("--no_stop_on_error", action="store_false", dest="stop_on_error", default=True, help="don't stop if there is an error from a player")
    parser.add_argument("--no_stop_on_illegal_play", action="store_false", dest="stop_on_illegal_play", default=True, help="don't stop if a player makes an illegal play")

    parser.add_argument("--no_show_player_stdout", action="store_false", dest="show_player_stdout", default=True, help="don't show (extra) player stdout if there is any")
    parser.add_argument("--no_hide_player_hands", action="store_false", dest="hide_player_hands", default=None, help="don't show player hands")
    parser.add_argument("--no_print_rerun_command", action="store_false", dest="print_rerun_command", default=True, help="don't print rerun command")
    parser.add_argument("--quiet", action="store_true", default=False, help="don't print any output during the game")
    parser.add_argument("--print_summary", action="store_true", default=False, help="print an easily-parsable summary at the end of the game")
    parser.add_argument("--tournament", action="store_true", default=False, help="make output suitable for a tournament")
    parser.add_argument("-i", "--interactive_player", action="store_true", default=False, help="add an interactive_player"
    )
    parser.add_argument("--upload_url", default='http://cgi.cse.unsw.edu.au/~cs1511/19T1/cgi/autotest_upload.cgi', help="URL for upload of results")
    parser.add_argument("--upload_max_bytes", default=2048000, type=int, help="MAX bytes in upload of results")
    parser.add_argument("--check", default='/home/cs1511/public_html/19T1/scripts/c_check', help="check C source")

    parser.add_argument("source_files",  nargs='*', default=[], help="")
    parser.add_argument("-d", "--debug", action="count", default=0,  help="show debug output")
#    parser.add_argument("--output_html", action="store_true", default=False, help="output_html")
#    parser.add_argument("-p", "--parameter", action="append", default=[], help="set parameter (name=value)")
    return parser.parse_args()

def post_process_args(args):
    if not args.quiet:
        print('Version:', VERSION, 'Hostname:', socket.gethostname())
    set_environment()

    if args.compiler == 'dcc':
        for compiler in "dcc clang gcc".split():
            if search_path(compiler):
                args.compiler = compiler
                break

    if args.compiler != 'dcc':
        args.valgrind = False

    if args.upload_url:
        save_source_files()

    if args.quiet and args.interactive_player:
        print("You can't play quietly with an interactive player!")
        exit(1)

    if args.hide_player_hands is None:
        args.hide_player_hands = args.interactive_player or args.quiet

    if args.tournament:
        os.nice(10)
        args.stop_on_illegal_play = False
        args.stop_on_error = False
        args.colorize = False
        args.show_player_stdout = False
        args.print_rerun_command = False

    if args.quiet:
        args.print_rerun_command = False

    global colored
    if args.colorize:
        colored = termcolor_colored
        os.environ['DCC_COLORIZE_OUTPUT'] = 'true'
    else:
        colored = lambda x, *args, **kwargs: x
def exit_game(extra_arguments=[]):
    if args.print_rerun_command:
        if not extra_arguments:
            print('You can rerun this game with this command:')
        print(rerun_command(extra_arguments))
        print()
        upload_source()
    sys.exit(0)

def rerun_command(extra=[]):
    if '-s' in sys.argv or '--seed' in  sys.argv:
        rerun_args = sys.argv[1:]
    else:
        rerun_args = ['-s', str(args.seed)] + sys.argv[1:]
    rerun_args = sys.argv[0:1] + extra + rerun_args
    return ' '.join(rerun_args)

def print_summary(finishing_positions):
    position = 1
    for (penalty_points, players) in finishing_positions:
        for player in players:
            print("{}\t{}\t{}".format(position, player['name'], penalty_points))
        position += len(players)

def play_game(players):
    players = copy.deepcopy(players)
    random.shuffle(players)
    for (i, player) in enumerate(players):
        player['table_position'] = i
        player['penalty_points'] = 0
    deal_hands(players)
    make_discards(players)
    cards_played_previous_rounds = []
    table_position_leading = 0
    for round in range(N_CARDS_IN_HAND):
        table_position_leading = play_round(round, players, table_position_leading, cards_played_previous_rounds)
    finishing_positions = calculate_finishing_positions(players)
    if not args.quiet:
        print_finishing_positions(finishing_positions)
    return finishing_positions

def play_round(round, players, table_position_leading, cards_played_previous_rounds):
    cards_played_current_round = []
    for n_cards_played in range(N_PLAYERS):
        table_position_playing = (table_position_leading + n_cards_played) % N_PLAYERS
        player = players[table_position_playing]
        card, illegal_explanation = get_play(player, cards_played_current_round, cards_played_previous_rounds)
        if not args.quiet:
            print_play(round, player, card, illegal_explanation)
        player['hand'].remove(card)
        if illegal_explanation:
            player['penalty_points'] += ILLEGAL_PLAY_PENALTY
        cards_played_current_round.append(card)
    cards_played_previous_rounds += cards_played_current_round
    winner_round = get_winner(table_position_leading, cards_played_current_round)
    round_penalties = sum(penalty(c) for c in cards_played_current_round)
    players[winner_round]['penalty_points'] += round_penalties
    if not args.quiet:
        print_round_winner(players[winner_round], round_penalties)
    return winner_round

def make_discards(players):
    if not args.quiet:
        print('Discards:')
    for player in players:
        discarded_cards, illegal_explanation = get_discards(player)
        player['discarded_cards'] = discarded_cards
        if not args.hide_player_hands:
            print(player['padded_colored_name'], end=' ')
            if illegal_explanation:
                print(illegal_explanation, ' referee chooses', end=' ')
            print(colored_card_list(discarded_cards))
    for player in players:
        passes_to_table_position = (player['table_position'] + 1) % N_PLAYERS
        passes_to_player = players[passes_to_table_position]
        passes_to_player['discards_received'] = player['discarded_cards']
        player['hand'] = player['hand'].difference(player['discarded_cards'])
        passes_to_player['hand'].update(player['discarded_cards'])
    print()
#   if not args.hide_player_hands:
#       print('After Discards:')
#       print_hands(players)
#       print()

def calculate_finishing_positions(players):
    penalties = collections.defaultdict(list)
    for player in players:
        penalties[player['penalty_points']].append(player)
    return sorted(penalties.items())

def print_finishing_positions(positions):
    print()
    print('Finishing Positions')
    print()
    position = 1
    for (penalty_points, players) in positions:
        for player in players:
            print("#{} with {} penalty points {} ({})".format(position, penalty_points, player['colored_name'], player['source']))
        position += len(players)
    print()

def print_round_winner(player, round_penalties):
    print("{} wins the round ".format(player['colored_name'],), end='')
    if round_penalties:
        print("which contains", colored("{} penalty points".format(round_penalties),'red'))
    else:
        print()
    print()

def get_play(player, cards_played_current_round, cards_played_previous_rounds):
    card, illegal_explanation = player['get_play'](player, cards_played_current_round, cards_played_previous_rounds)
    if illegal_explanation:
        random_card = random_play(player, cards_played_current_round, cards_played_previous_rounds)
        return random_card, 'plays the {} - {}'.format(colored_card(card), illegal_explanation)
    else:
        return card, ''

def get_discards(player):
    discards, illegal_explanation = player['get_discards'](player)
    if illegal_explanation:
        return set(random_discards(player)), 'discards {} - {}'.format(colored_card_list(discards), illegal_explanation)
    else:
        return set(discards), ''

def print_play(round, player, card, illegal_explanation):
    card = colored_card(card)
    hand = colored_card_list(player['hand'])
    print(f"Round {round}: {player['padded_colored_name']} ", end='')
    if not args.hide_player_hands:
        print(f"holding {hand} ", end='')
    if illegal_explanation:
        print(f"{illegal_explanation}: {ILLEGAL_PLAY_PENALTY} penalty points - referee chooses {card} ", end='')
    else:
        print(f'plays the {card} ', end='')
    print()

def get_winner(player_leading, cards_played_current_round):
    first_card_played = cards_played_current_round[0]
    if prime(first_card_played):
        following_first_play = prime
    else:
        following_first_play = lambda card: card in COCOMPOSITE_WITH[first_card_played]
    following_plays = [(card,w) for (w,card) in enumerate(cards_played_current_round) if following_first_play(card)]
    #print('follwing_plays', following_plays, max(following_plays)[1])
    if following_plays:
        return (player_leading + max(following_plays)[1]) % N_PLAYERS
    return player_leading

def get_legal_plays(hand, cards_played_current_round, cards_played_previous_rounds):
    if cards_played_current_round:
        first_card_played = cards_played_current_round[0]
        if prime(first_card_played):
            prime_cards = set(c for c in hand if prime(c))
            if prime_cards:
                return list(prime_cards)
        else:
            cocomposite_cards = set(hand) & COCOMPOSITE_WITH[cards_played_current_round[0]]
            if cocomposite_cards:
                return list(cocomposite_cards)
        return hand
    if any(card for card in cards_played_previous_rounds if prime(card)):
        return hand
    non_prime_cards = [card for card in hand if not prime(card)]
    if non_prime_cards:
        return non_prime_cards
    return hand

def explain_illegal_play(card, hand, cards_played_current_round, cards_played_previous_rounds):
    if card < str(CARD_MIN) or card > str(CARD_MAX):
        return 'not a valid card'
    if card not in hand:
        return 'card not in hand'
    if cards_played_current_round:
        first_card_played = cards_played_current_round[0]
        if prime(first_card_played):
            prime_cards = set(c for c in hand if prime(c))
            if prime_cards and card not in prime_cards:
                return f'The first card played in this round was {first_card_played} which is prime but {card} is not prime'
        else:
            cocomposite_cards = set(hand) & COCOMPOSITE_WITH[cards_played_current_round[0]]
            if cocomposite_cards and card not in cocomposite_cards:
                return f'{card} is not cocomposite with the first card played in this round which was {cards_played_current_round[0]}'
        return ''
    if any(card for card in cards_played_previous_rounds if prime(card)):
        return ''
    non_prime_cards = [card for card in hand if not prime(card)]
    if non_prime_cards and card not in non_prime_cards:
        return f'{card} is prime and a prime can not be played as first card in a round until a prime has been played in a previous round, or a player has no choice.'
    return ''

def prime(card):
    return not COCOMPOSITE_WITH[card]


def explain_illegal_discards(discards, hand):
    if len(set(discards)) != len(discards):
        return 'repeated discard'
    discards = set(discards)
    if len(discards) != N_CARDS_DISCARDED:
        return 'incorrect number of discards'
    if discards.issubset(hand):
        return ''
    return 'card not in hand'

def deal_hands(players):
    deck = list(range(CARD_MIN, CARD_MIN + N_CARDS_IN_HAND*N_PLAYERS))
    random.shuffle(deck)
    for (i, player) in enumerate(players):
        cards = deck[i * N_CARDS_IN_HAND : (i + 1) * N_CARDS_IN_HAND]
        player['hand'] = set(map(str, cards))
    if not args.hide_player_hands:
        print('Deal:')
        print_hands(players)

def print_hands(players):
    for player in players:
        cards = colored_card_list(player['hand'])
        print("Table position {}: {}: {}".format(player['table_position'], player['padded_colored_name'], cards))
    print()

def penalty(card):
    if card == SPECIAL_CARD:
        return SPECIAL_CARD_PENALTY
    elif not COCOMPOSITE_WITH[card]:
        return PRIME_PENALTY
    else:
        return 0

def interactive_discarder(player):
    print()
    print(player['colored_name'], 'must choose discards.')
    print(player['colored_name'], 'have in your hand:', colored_card_list(player['hand']))
    discards = interactive_input("Enter cards to discard: ")
    print()
    discards = re.findall(r'\d+', discards)
    explanation = explain_illegal_discards(discards, player['hand'])
    if not explanation:
        return discards, ''
    if discards:
        print('Illegal discards: ', colored(explanation, 'red'))
    return interactive_discarder(player)

def interactive_player(player, cards_played_current_round, cards_played_previous_rounds):
    print()
    legal_plays = get_legal_plays(player['hand'], cards_played_current_round, cards_played_previous_rounds)
    print(player['colored_name'], 'have to play.')
    print(player['colored_name'], 'have in your hand:', colored_card_list(player['hand']))
    card = interactive_input("Enter card to play: ")
    card = card.strip()
    print()
    explanation = explain_illegal_play(card, player['hand'], cards_played_current_round, cards_played_previous_rounds)
    if not explanation:
        return card, ''
    if card:
        print('Illegal play:',  colored(explanation, 'red'))
        print('Legal plays are:', colored_card_list(legal_plays))
    return interactive_player(player, cards_played_current_round, cards_played_previous_rounds)

def interactive_input(prompt):
    try:
        return input(prompt)
    except EOFError:
        sys.exit(1)
    except UnicodeDecodeError:
        return ''

def random_discarder(player):
    return random_discards(player), ''

def random_discards(player):
    return random.sample(sorted(player['hand']), N_CARDS_DISCARDED)

def random_player(player, cards_played_current_round, cards_played_previous_rounds):
    return random_play(player, cards_played_current_round, cards_played_previous_rounds), ''

def random_play(player, cards_played_current_round, cards_played_previous_rounds):
    legal_plays = get_legal_plays(player['hand'], cards_played_current_round, cards_played_previous_rounds)
    return random.choice(sorted(legal_plays))

def run_binary_for_player_name(player):
    input = '{}\n'.format(ACTION_PLAYER_NAME)
    stdout = run_binary(player, input=input)
    return stdout if stdout else "The Unknown Player"

def run_binary_for_discards(player):
    input = '{}\n'.format(ACTION_DISCARD)
    input += ' '.join(sorted(player['hand'])) + '\n'
    stdout = run_binary(player, input=input)
    if not re.match(r'^\s*\d\d\s+\d\d\s+\d\d\s*$', stdout) and args.show_player_stdout:
        # let debugging output through - turn off for tournaments
        print()
        print('Output from', player['colored_name'],)
        print(stdout)
        print()
    discards = re.findall(r'\d\d', stdout)[-N_CARDS_DISCARDED:]
    explanation = explain_illegal_discards(discards, player['hand'])
    if not explanation:
        return discards, ''
    if args.stop_on_illegal_play:
        print()
        print('Game stopped stopped due to illegal discards by', player['name'])
        print('Discards:', colored_card_list(discards))
        print('Explanation:', colored(explanation, 'red'))
        print('Hand was:', colored_card_list(player['hand']))
        print()
        print('To reproduce these illegal discards from your program run:')
        print(colored('echo -e "{}"|./coco'.format(input.rstrip().replace('\n', '\\n')), 'red'))
        print()
        print('Stopping game.  To run this game without stopping for illegal plays use --no_stop_on_illegal_play:')
        exit_game(['--no_stop_on_illegal_play'])
    return discards, 'illegal discard'

def run_binary_for_play(player, cards_played_current_round, cards_played_previous_rounds):
    input = '{}\n'.format(ACTION_PLAY_CARD)
    input += '{} {} {}\n'.format(len(player['hand']), len(cards_played_current_round), player['table_position'], )
    input += ' '.join(sorted(player['hand'])) + '\n'
    input += ' '.join(cards_played_current_round) + '\n'
    input += '\n'.join(cards_played_previous_rounds) + '\n'
    input += '\n'.join(sorted(player['discarded_cards'])) + '\n'
    input += '\n'.join(sorted(player['discards_received'])) + '\n'
    stdout = run_binary(player, input=input)
    if stdout and not re.match(r'^\s*\d{1,2}\s*$', stdout) and args.show_player_stdout:
         # let debugging output through
        print()
        print('Debug output from', player['colored_name'])
        print(hr())
        print(stdout, end='')
        print(hr())
        print()
    numbers = re.findall(r'\d\d', stdout)
    numbers = numbers if numbers else re.findall(r'\d', stdout)
    if numbers:
        card = numbers[-1]
        explanation = explain_illegal_play(card, player['hand'], cards_played_current_round, cards_played_previous_rounds)
        if not explanation:
            return card, explanation
    else:
        card = ''
        explanation = 'program output not an integer' if stdout else 'no output from program'

    if args.stop_on_illegal_play:
        print()
        print('Game stopped stopped due to illegal play by', player['name'])
        print('Card played:', card)
        print('Explanation:', colored(explanation, 'red'))
        legal_plays = get_legal_plays(player['hand'], cards_played_current_round, cards_played_previous_rounds)
        print('Hand was:', colored_card_list(player['hand']))
        print('Legal plays were:', colored_card_list(legal_plays))
        print()
        print('To reproduce this illegal play from your program run:')
        print(colored('echo -e "{}"|./coco'.format(input.rstrip().replace('\n', '\\n')), 'red'))
        print()
        print('Stopping game.  To run this game without stopping for illegal plays use --no_stop_on_illegal_play:')
        exit_game(['--no_stop_on_illegal_play'])
    return card, explanation

def run_binary(player, input=''):
    (stdout, stderr, exit_status, binary) = run_dual(player['binary'], input=input)
    if stderr and exit_status != 0:
        print('Errors from', player['colored_name'],)
        print(hr())
        print(stderr)
        print(hr())
        if args.stop_on_error:
            print()
            print('To reproduce this error run:')
            source = player['source']
            if player['source'].endswith('.c'):
                if binary.endswith('valgrind'):
                    print(colored(f'dcc --valgrind {source} -o coco', 'red'))
                else:
                    print(colored(f'dcc {source} -o coco', 'red'))
                binary = './coco'
            else:
                binary = source
            input_or_echo = input.rstrip().replace('\n', '\\n')
            print(colored(f'echo -e "{input_or_echo}"|{binary}', 'red'))
            print()
            print('Stopping game.  To run this game without stopping for errors use --no_stop_on_error:')
            exit_game(['--no_stop_on_error'])
        return ''
    if stderr and args.show_player_stdout:
        # let debugging output through - turn off for tournaments
        print()
        print('Debug output on stderr from', player['colored_name'],)
        print(hr())
        print(stderr, end='')
        print(hr())
        print()
    return stdout

def hr():
    return '-'*72

def run_dual(binary, arguments=[], input=''):
    output = []
    binaries = [binary]
    valgrind_binary = binary + '-valgrind'
    if os.path.exists(valgrind_binary):
        binaries += [valgrind_binary]
    for b in binaries:
        for attempt in range(3):
            if isinstance(input, str):
                input_str = input
                input = input.encode('ascii')
            else:
                input_str = input.decode('ascii', errors='replace')
            (stdout, stderr, exit_status) = run_with_resource_limits([b]+arguments, input=input)
            stdout = codecs.decode(stdout, 'ascii', errors='replace')
            stderr = codecs.decode(stderr, 'ascii', errors='replace')

            if args.debug and input:
                print('echo -e "{}"|{}'.format(input_str.rstrip().replace('\n', '\\n'), ' '.join([b]+arguments)))
            if stderr and exit_status != 0:
                return (stdout, stderr, exit_status, b)
            if not stdout and exit_status != 0:
                # weird termination with non-zero exit status seen on some CSE servers
                # ignore this execution
                time.sleep(1)
                continue
            output.append((stdout, stderr, exit_status, b))
            break
    return output[0] if output else ('', '', 1, binary)

def compile_program(args, dir=None, binary='coco', valgrind=False):
    if dir:
        os.chdir(dir)
    source_files = glob.glob('*.c')
    compilers = [[args.compiler, '-o', binary]]
    if valgrind:
         compilers += [['dcc', '--valgrind', '-o', binary+'-valgrind']]
    for compiler in compilers:
        try:
            command = compiler + source_files
            if not args.quiet:
                print(' '.join(command))
            subprocess.check_call(command)
        except subprocess.CalledProcessError:
            sys.exit(1)
    if not args.quiet:
        print()
    if args.check:
        try:
            subprocess.call([args.check] + source_files)
        except OSError:
            pass
    return os.path.realpath(binary)

def cleanup(temp_dir=None):
    if temp_dir and re.search('^/tmp/', temp_dir) and args.debug < 2:
        shutil.rmtree(temp_dir)
    if args.debug > 1:
        print('leaving', temp_dir)

def compile_players(args):
    player_dirs = []
    temp_dir = None
    binaries = []
    for (player_number,path) in enumerate(args.source_files):
        if not temp_dir:
            temp_dir = tempfile.mkdtemp()
            atexit.register(cleanup, temp_dir=temp_dir)
        player_dir = os.path.join(temp_dir, str(player_number))
        os.mkdir(player_dir)
        if os.path.isdir(path):
            for file in glob.glob(os.path.join(path, '*.[ch]')) + glob.glob(os.path.join(path, '*.txt')):
                try:
                    shutil.copy(file, player_dir)
                except IOError:
                    print(sys.argv[0], 'could not open', file, file=sys.stderr)
            player_dirs.append(player_dir)
        elif re.search(r'\b(tar|tgz)\b', path):
            if subprocess.run(['tar', '-x', '-C', player_dir, '-f', path, '--exclude', 'trader_player.h']).returncode != 0:
                print("Can not extract tar file '{}'".format(path), file=sys.stderr)
                sys.exit(1)
            player_dirs.append(player_dir)
        elif os.path.splitext(path)[1] in ['.c']:
            try:
                shutil.copy(path, player_dir)
            except IOError:
                print(sys.argv[0], 'could not open', path, file=sys.stderr)
                sys.exit(1)
            player_dirs.append(player_dir)
        elif os.path.isfile(path) and os.access(path, os.X_OK):
#            realpath = os.path.realpath(path)
#            realpath = re.sub(r'/tmp_amd/\w+/\w+/\w+/\d+/', '/home/', realpath)
            basename = os.path.basename(path)
            newpath = os.path.join(player_dir, basename)
            try:
                shutil.copy(path, newpath)
            except OSError:
                print(sys.argv[0], 'could not copy', path, file=sys.stderr)
                sys.exit(1)
            try:
                shutil.copy(path + "-valgrind", newpath + "-valgrind")
            except OSError:
                if args.debug:
                    print('no valgrind binary found')
                pass
            binaries.append(newpath)
        else:
            print('Unexpected argument:', path, file=sys.stderr)
            sys.exit(1)
    for player_dir in player_dirs:
        binaries.append(compile_program(args, dir=player_dir, valgrind=args.valgrind))
    return binaries

def sanitize_player_names(players):
    names = set()
    for player in players:
        name = player['name']
        prefix = re.sub(r"[^a-zA-Z0-9' _-]", '', name)[0:MAX_SUPPLIED_PLAYER_NAME_CHARS]
        i = 0
        name = prefix
        while name in names:
            name = prefix + str(i)
            i += 1
        player['name'] = name
        names.add(name)

def color_player_names(players):
    colors ="cyan green blue magenta".split()
    max_player_name_len = max(len(player['name']) for player in players)
    for (player,color) in zip(players,colors):
        name = player['name']
        attrs = [] if player['system'] else ['underline']
        player['colored_name'] = colored(name, color, attrs=attrs)
        padding = (' ' * (max_player_name_len - len(name)))
        player['padded_colored_name'] = player['colored_name'] + padding

def colored_card_list(card_list):
    return '['+ ", ".join(map(colored_card, sorted(map(str, card_list)))) + ']'

def colored_card(card):
    if card == SPECIAL_CARD:
        return colored(card, color='red')
    elif not COCOMPOSITE_WITH.get(card, ''):
        return colored(card, color='yellow')
    else:
        return card

def set_environment():
    for variable in list(os.environ.keys()):
        os.environ.pop(variable, None)
    os.environ['LANG'] = 'en_AU.utf8'
    os.environ['LANGUAGE'] = 'en_AU.UTF-8'
    os.environ['LC_ALL'] = 'en_AU.UTF-8'
    os.environ['LC_COLLATE'] = 'POSIX'
    os.environ['PATH'] = '/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:.'

def search_path(program):
    for path in os.environ["PATH"].split(os.pathsep):
        full_path = os.path.join(path, program)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path

def save_source_files():
    args.source_file_contents = {}
    bytes_to_be_uploaded =0
    for source_file in args.source_files:
        if not source_file.endswith('.c'):
            continue
        basename = os.path.basename(source_file)
        if basename in args.source_file_contents:
            continue
        try:
            bytes_to_be_uploaded += os.path.getsize(source_file)
            if bytes_to_be_uploaded > args.upload_max_bytes:
                break
            with open(source_file, encoding='ascii') as f:
                args.source_file_contents[basename] = f.read()
        except (OSError, UnicodeDecodeError) as e:
            if args.debug:
                print(str(e))

def upload_source():
    if not args.source_files or not args.upload_url or not requests_post:
        return
    zid = get_zid()
    if not zid:
        return
    buffer = io.BytesIO()
    zf = zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_LZMA)
    try:
        zf.writestr('seed.txt', str(args.seed) + "\n")
        zf.writestr('rerun.txt', rerun_command() + "\n")
        for (source_file_name, contents) in args.source_file_contents.items():
            if args.debug:
                print('uploading', source_file_name)
            zf.writestr(source_file_name, contents)
    except AttributeError as e:
        if args.debug:
            print(e)
        pass
    zf.close()
    buffer.seek(0)
    parameters = {"zid" : zid, "exercise" : 'coco_referee'}
    if args.debug:
        print(args.upload_url)
    r = requests_post(args.upload_url, data=parameters, files={"zip": ("zip", buffer)})
    if args.debug:
        print(r.text)

def get_zid():
    try:
        # os.getlogin() may fail,
        # unclear if pwd.getpwuid(os.getuid())[0] would be better
        # we aren't trusting the zid anyway
        account = getpass.getuser()

        if account == 'andrewt':
            return 'z9300162'
        if re.search(r'^z\d{7}$', account):
            return account
    except OSError as e:
        if args.debug:
            print(e)
        pass

# Ugly workarounds to produce somewhat portable code that runs standalone
# but add some extra features at CSE.
#
# The subprocess_with_resource_limits & termcolor code may not
# be portable (e.g. to windows)  so is not embedded but rather imported if available
def do_imports():
    sys.path.append('/home/cs1511/public_html/19T1/scripts/')
    global run_with_resource_limits
    try:
        import subprocess_with_resource_limits
        def run_with_resource_limits(*args, **kwargs):
            return subprocess_with_resource_limits.run(*args, **kwargs, max_cpu=30, max_wall_clock=120, nice=5)
    except ImportError:
        def run_with_resource_limits(*args, **kwargs):
            p = subprocess.run(*args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
            return (p.stdout, p.stderr, p.returncode)

    global termcolor_colored
    try:
        from termcolor import colored as termcolor_colored
    except ImportError:
        termcolor_colored = lambda x, *args, **kwargs: x

    # Allow code (except source upload) to run if requests not available

    global requests_post
    try:
        import requests
        requests_post = requests.post
    except ImportError:
        requests_post = None

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda signum, frame:sys.exit(1))
    do_imports()
    main()
