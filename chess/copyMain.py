import pygame as pg
import pygame_gui
from pygame_gui.elements import UIButton
from multiprocessing import Queue, Process
import copyEngine
import chessAI
import cv2
import numpy as np

pg.init()

# Global Constants
BOARD_WIDTH = BOARD_HEIGHT =789
MOVE_LOG_WIDTH = 225
MOVE_LOG_HEIGHT = BOARD_HEIGHT
DIMENSION = 8
SQ_SIZE = BOARD_WIDTH // DIMENSION
MAX_FPS = 15
IMAGES = {}
SOUNDS = {}

# Constants for UI
BUTTON_WIDTH = 150
BUTTON_HEIGHT = 50

# Colors
WHITE = pg.Color("white")
BLACK = pg.Color("black")
GOLDENROD = pg.Color("goldenrod")

def initialize_game(difficulty):
    if difficulty == "Easy":
        chessAI.MAX_DEPTH = 2
    elif difficulty == "Intermediate":
        chessAI.MAX_DEPTH = 3
    elif difficulty == "Hard":
        chessAI.MAX_DEPTH = 4

def load_images():
    pieces = ["wp", "bp", "wR", "bR", "wN", "bN", "wB", "bB", "wQ", "bQ", "wK", "bK"]
    for piece in pieces:
        IMAGES[piece] = pg.transform.scale(pg.image.load("images/" + piece + ".png"), (64, 64))

def load_sounds():
    sounds = ["capture", "draw", "move-self", "game_over"]
    for sound in sounds:
        SOUNDS[sound] = pg.mixer.Sound("sounds/" + sound + ".wav")

def create_starting_screen(screen):
    # Load background image
    background_image = pg.image.load('images/background_image.png')
    background_image = pg.transform.scale(background_image, (BOARD_WIDTH, BOARD_HEIGHT))

    # Draw the background image
    screen.blit(background_image, (0, 0))

    # Add UI manager
    gui_manager = pygame_gui.UIManager((BOARD_WIDTH + MOVE_LOG_WIDTH, BOARD_HEIGHT))

    # Add buttons with different blur levels
    easy_button = UIButton(
        relative_rect=pg.Rect((BOARD_WIDTH // 2 - BUTTON_WIDTH // 2, 150), (BUTTON_WIDTH, BUTTON_HEIGHT)),
        text='Easy', manager=gui_manager)

    intermediate_button = UIButton(
        relative_rect=pg.Rect((BOARD_WIDTH // 2 - BUTTON_WIDTH // 2, 220), (BUTTON_WIDTH, BUTTON_HEIGHT)),
        text='Intermediate', manager=gui_manager)

    hard_button = UIButton(
        relative_rect=pg.Rect((BOARD_WIDTH // 2 - BUTTON_WIDTH // 2, 290), (BUTTON_WIDTH, BUTTON_HEIGHT)),
        text='Hard', manager=gui_manager)

    return gui_manager, easy_button, intermediate_button, hard_button

def main():
    pg.init()

    # Load chessboard image
    chessboard_image = pg.image.load('images/background_image.png')
    chessboard_image = pg.transform.scale(chessboard_image, (BOARD_WIDTH, BOARD_HEIGHT))
    screen = pg.display.set_mode((BOARD_WIDTH + MOVE_LOG_WIDTH, BOARD_HEIGHT))
    clock = pg.time.Clock()
    screen.fill(WHITE)
    gs = copyEngine.GameState()
    valid_moves = gs.get_valid_moves()
    move_log_font = pg.font.SysFont("Arial", 15, True, False)
    move_made = False
    animate = False
    game_over = False
    game_over_sound_played = False
    draw_sound_played = False
    load_images()
    load_sounds()
    running = True
    sq_selected = ()
    player_clicks = []
    player_one = True
    player_two = False
    ai_thinking = False
    move_finder_process = None
    move_undone = False

    gui_manager = pygame_gui.UIManager((BOARD_WIDTH + MOVE_LOG_WIDTH, BOARD_HEIGHT))

    # Add buttons with different blur levels
    easy_button = UIButton(
        relative_rect=pg.Rect((BOARD_WIDTH, 50), (BUTTON_WIDTH, BUTTON_HEIGHT)),
        text='Easy', manager=gui_manager)

    intermediate_button = UIButton(
        relative_rect=pg.Rect((BOARD_WIDTH, 110), (BUTTON_WIDTH, BUTTON_HEIGHT)),
        text='Intermediate', manager=gui_manager)

    hard_button = UIButton(
        relative_rect=pg.Rect((BOARD_WIDTH, 170), (BUTTON_WIDTH, BUTTON_HEIGHT)),
        text='Hard', manager=gui_manager)

    running = True
    difficulty_selected = None

    screen = pg.display.set_mode((BOARD_WIDTH + MOVE_LOG_WIDTH, BOARD_HEIGHT))
    pg.display.set_caption("Chess Game")

    gui_manager = create_starting_screen(screen)
    
    clock = pg.time.Clock()
    running = True
    difficulty_selected = None

    gui_manager, easy_button, intermediate_button, hard_button = create_starting_screen(screen)

    # ...

    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.MOUSEBUTTONDOWN:
                if easy_button.rect.collidepoint(event.pos):
                    difficulty_selected = "Easy"
                elif intermediate_button.rect.collidepoint(event.pos):
                    difficulty_selected = "Intermediate"
                elif hard_button.rect.collidepoint(event.pos):
                    difficulty_selected = "Hard"

        gui_manager.process_events(event)  # Process events inside the loop

        gui_manager.update(0.0)
        gui_manager.draw_ui(screen)

        pg.display.flip()

        if difficulty_selected:
            break

    if difficulty_selected:
        initialize_game(difficulty_selected)

    while running:
        human_turn = (gs.whiteToMove and player_one) or (not gs.whiteToMove and player_two)
        for e in pg.event.get():
            if e.type == pg.QUIT:
                running = False
            elif e.type == pg.MOUSEBUTTONDOWN:
                if not game_over:
                    location = pg.mouse.get_pos()
                    cols = location[0] // SQ_SIZE
                    row = location[1] // SQ_SIZE
                    if sq_selected == (row, cols):
                        sq_selected = ()
                        player_clicks = []
                    else:
                        sq_selected = (row, cols)
                        player_clicks.append(sq_selected)
                    if len(player_clicks) == 2 and human_turn:
                        move = copyEngine.Move(player_clicks[0], player_clicks[1], gs.board)
                        print(move.get_chess_notation())
                        for i in range(len(valid_moves)):
                            if move == valid_moves[i]:
                                if move.piece_captured != "--":
                                    pg.mixer.Sound.play(SOUNDS["capture"])
                                else:
                                    pg.mixer.Sound.play(SOUNDS["move-self"])
                                gs.make_move(valid_moves[i])
                                move_made = True
                                animate = True
                                sq_selected = ()
                                player_clicks = []
                        if not move_made:
                            player_clicks = [sq_selected]
            elif e.type == pg.KEYDOWN:
                if e.key == pg.K_z:
                    gs.undo_move()
                    move_made = True
                    animate = False
                    game_over = False
                    draw_sound_played = False
                    game_over_sound_played = False
                    if ai_thinking:
                        move_finder_process.terminate()
                        ai_thinking = False
                    move_undone = True
                if e.key == pg.K_r:
                    gs = copyEngine.GameState()
                    valid_moves = gs.get_valid_moves()
                    sq_selected = ()
                    player_clicks = []
                    animate = False
                    move_made = False
                    game_over = False
                    draw_sound_played = False
                    game_over_sound_played = False
                    if ai_thinking:
                        move_finder_process.terminate()
                        ai_thinking = False
                    move_undone = True

        if not game_over and not human_turn and not move_undone:
            if not ai_thinking:
                ai_thinking = True
                print("thinking...")
                return_queue = Queue()
                move_finder_process = Process(target=chessAI.find_best_move, args=(gs, valid_moves, return_queue))
                move_finder_process.start()

            if not move_finder_process.is_alive():
                print("Done Thinking")
                ai_move = return_queue.get()
                if ai_move is None:
                    ai_move = chessAI.find_random_move(valid_moves)
                gs.make_move(ai_move)
                move_made = True
                animate = True
                ai_thinking = False

        if move_made:
            if animate:
                animate_move(gs.moveLog[-1], screen, gs.board, clock)
            valid_moves = gs.get_valid_moves()
            move_made = False
            animate = False
            move_undone = False

        draw_game_state(screen, gs, valid_moves, sq_selected, gs.whiteKingLocation, gs.blackKingLocation, move_log_font)

        if gs.inCheck:
            if gs.checkMate:
                game_over = True
                if not game_over_sound_played:
                    pg.mixer.Sound.play(SOUNDS["game_over"])
                    game_over_sound_played = True
                if gs.whiteToMove:
                    draw_end_game_text(screen, "Black Wins")
                else:
                    draw_end_game_text(screen, "White Wins")
        if gs.staleMate:
            if not draw_sound_played:
                pg.mixer.Sound.play(SOUNDS["draw"])
                pg.time.delay(100)
                draw_sound_played = True
            game_over = True
            draw_end_game_text(screen, "Draw")
        pg.display.flip()

def highlight_square(screen, gs, valid_moves, sq_selected):
    if sq_selected != ():
        row, col = sq_selected
        if gs.board[row][col][0] == ("w" if gs.whiteToMove else "b"):
            s = pg.Surface((SQ_SIZE, SQ_SIZE))
            s.set_alpha(255)
            s.fill(GOLDENROD)
            screen.blit(s, (col * SQ_SIZE, row * SQ_SIZE))
            s.set_alpha(150)
            s.fill(GOLDENROD)
            for move in valid_moves:
                if move.start_row == row and move.start_cols == col:
                    screen.blit(s, (move.end_cols * SQ_SIZE, move.end_row * SQ_SIZE))

def check(screen, w_location, b_location, gs):
    if gs.inCheck:
        if gs.whiteToMove:
            row, col = w_location[0], w_location[1]
            s = pg.Surface((SQ_SIZE, SQ_SIZE))
            s.set_alpha(225)
            s.fill(pg.Color('red'))
            screen.blit(s, pg.Rect(col * SQ_SIZE, row * SQ_SIZE, SQ_SIZE, SQ_SIZE))
        else:
            row, col = b_location[0], b_location[1]
            s = pg.Surface((SQ_SIZE, SQ_SIZE))
            s.set_alpha(225)
            s.fill(pg.Color('red'))
            screen.blit(s, pg.Rect(col * SQ_SIZE, row * SQ_SIZE, SQ_SIZE, SQ_SIZE))

def draw_game_state(screen, gs, valid_moves, sq_selected, w_location, b_location, move_log_font):
    draw_board(screen)
    highlight_square(screen, gs, valid_moves, sq_selected)
    check(screen, w_location, b_location, gs)
    draw_pieces(screen, gs.board)
    draw_move_log(screen, gs, move_log_font)

def draw_board(screen):
    colors = [pg.Color("beige"), pg.Color("light green")]
    for row in range(DIMENSION):
        for cols in range(DIMENSION):
            color = colors[((row+cols) % 2)]
            pg.draw.rect(screen, color, pg.Rect(cols*SQ_SIZE, row*SQ_SIZE, SQ_SIZE, SQ_SIZE))
    pg.display.set_caption("CHESS")

def draw_pieces(screen, board):
    for row in range(DIMENSION):
        for cols in range(DIMENSION):
            piece = board[row][cols]
            if piece != "--":
                screen.blit(IMAGES[piece], pg.Rect(cols*SQ_SIZE, row*SQ_SIZE, SQ_SIZE, SQ_SIZE))

def animate_move(move, screen, board, clock):
    beige = (245, 245, 220)
    dark_green = (0, 100, 0)
    colors = (beige, dark_green)
    d_r = move.end_row - move.start_row
    d_c = move.end_cols - move.start_cols
    frames_per_square = 8
    frame_count = (abs(d_r) + abs(d_c)) * frames_per_square
    for frame in range(frame_count + 1):
        r, c = (move.start_row + d_r * frame/frame_count, move.start_cols + d_c * frame/frame_count)
        draw_board(screen)
        draw_pieces(screen, board)
        color = colors[(move.end_row + move.end_cols) % 2]
        end_square = pg.Rect(move.end_cols * SQ_SIZE, move.end_row * SQ_SIZE, SQ_SIZE, SQ_SIZE)
        pg.draw.rect(screen, color, end_square)
        if move.piece_captured != '--':
            if move.is_en_passant_move:
                en_passant_row = move.end_row + 1 if move.piece_captured[0] == 'b' else move.end_row - 1
                end_square = pg.Rect(move.end_cols * SQ_SIZE, en_passant_row * SQ_SIZE, SQ_SIZE, SQ_SIZE)
            screen.blit(IMAGES[move.piece_captured], end_square)
        screen.blit(IMAGES[move.piece_moved], pg.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))
        pg.display.flip()
        clock.tick(100)

def draw_move_log(screen, gs, font):
    move_log_rect = pg.Rect(BOARD_WIDTH, 0, MOVE_LOG_WIDTH, MOVE_LOG_HEIGHT)
    pg.draw.rect(screen, BLACK, move_log_rect)
    move_log = gs.moveLog
    move_texts = []
    for i in range(0, len(move_log), 2):
        move_string = str(i // 2 + 1) + "." + str(move_log[i]) + " "
        if i + 1 < len(move_log):
            move_string += str(move_log[i+1]) + "  "
        move_texts.append(move_string)
    moves_per_row = 3
    padding = 5
    line_spacing = 2
    text_y = padding
    for i in range(0, len(move_texts), moves_per_row):
        text = ""
        for j in range(moves_per_row):
            if i + j < len(move_texts):
                text += move_texts[i + j]
        text_object = font.render(text, True, WHITE)
        text_location = move_log_rect.move(padding, text_y)
        screen.blit(text_object, text_location)
        text_y += text_object.get_height() + line_spacing

def draw_end_game_text(screen, text):
    font = pg.font.SysFont("arial", 32, True, False)
    text_object = font.render(text, False, BLACK)
    text_location = pg.Rect(0, 0, BOARD_WIDTH, BOARD_HEIGHT).move(BOARD_WIDTH / 2 - text_object.get_width() / 2,
                                                                  BOARD_HEIGHT / 2 - text_object.get_height() / 2)
    screen.blit(text_object, text_location)
    text_object = font.render(text, False, pg.Color("gray"))
    screen.blit(text_object, text_location.move(2, 2))

if __name__ == "__main__":
    main()
