#!/usr/bin/env python3
# vim: tw=76

import kxg
import random
import pyglet

LOWER_BOUND, UPPER_BOUND = 0, 5000

class World(kxg.World):
    """
    Keep track of the secret number, the range of numbers that haven't been 
    eliminated yet, and the winner (if there is one).
    """

    def __init__(self):
        super().__init__()
        self.number = 0
        self.lower_bound = 0
        self.upper_bound = 0
        self.winner = 0


class Referee(kxg.Referee):
    """
    Pick the secret number.
    """

    def on_start_game(self, num_players):
        number = random.randint(LOWER_BOUND + 1, UPPER_BOUND - 1)
        self >> PickNumber(number, LOWER_BOUND, UPPER_BOUND)


class PickNumber(kxg.Message):
    """
    Pick the secret number and communicate that choice to all the clients.
    """

    def __init__(self, number, lower_bound, upper_bound):
        self.number = number
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    def on_check(self, world):
        if world.number:
            raise kxg.MessageCheck("number already picked")

    def on_execute(self, world):
        world.number = self.number
        world.lower_bound = self.lower_bound
        world.upper_bound = self.upper_bound


class GuessNumber(kxg.Message):
    """
    Make a guess on behalf of the given player.  If the guess is 
    right, that player wins the game.  If the guess is wrong, the 
    range of numbers that the secret number could be is narrowed 
    accordingly.
    """

    def __init__(self, player, guess):
        self.player = player
        self.guess = guess

    def on_check(self, world):
        pass

    def on_execute(self, world):
        if self.guess == world.number:
            world.winner = self.player
            world.end_game()

        elif self.guess < world.number:
            world.lower_bound = max(self.guess, world.lower_bound)

        elif self.guess > world.number:
            world.upper_bound = min(self.guess, world.upper_bound)


class Gui:
    """
    Manage GUI objects like the window, which exist before and after the game 
    itself.
    """

    def __init__(self):
        self.width, self.height = 600, 400
        self.window = pyglet.window.Window()
        self.window.set_size(self.width, self.height)
        self.window.set_visible(True)
        self.label = pyglet.text.Label(
                "",
                color=(255, 255, 255, 255),
                font_name='Deja Vu Sans', font_size=32,
                x=self.width//2, y=self.height//2,
                anchor_x='center', anchor_y='center',
        )

    def on_refresh_gui(self):
        self.window.clear()
        self.label.draw()


class GuiActor(kxg.Actor):
    """
    Show the players the range of numbers that haven't been eliminated yet,
    and allow the player to guess what the number is.
    """

    def __init__(self):
        super().__init__()
        self.guess = None
        self.prompt = "{0.lower_bound} < {1} < {0.upper_bound}"

    def on_setup_gui(self, gui):
        self.gui = gui
        self.gui.window.set_handlers(self)

    def on_draw(self):
        self.gui.on_refresh_gui()

    def on_mouse_scroll(self, x, y, dx, dy):
        if self.guess is None:
            if dy < 0:
                self.guess = self.world.upper_bound
            else:
                self.guess = self.world.lower_bound

        self.guess = sorted([
            self.world.lower_bound,
            self.guess + dy,
            self.world.upper_bound,
        ])[1]

        self.on_update_prompt()

    def on_key_press(self, symbol, modifiers):
        # If the user types a number, add that digit to the guess.
        try:
            digit = int(chr(symbol))
            self.guess = 10 * (self.guess or 0) + digit
        except ValueError:
            pass
        
        # If the user hits backspace, remove the last digit from the guess.
        if symbol == pyglet.window.key.BACKSPACE:
            if self.guess is not None:
                guess_str = str(self.guess)[:-1]
                self.guess = int(guess_str) if guess_str else None

        # If the user hits enter, guess the current number.
        if symbol == pyglet.window.key.ENTER:
            if self.guess:
                self >> GuessNumber(self.id, self.guess)
                self.guess = None

        self.on_update_prompt()

    @kxg.subscribe_to_message(PickNumber)
    @kxg.subscribe_to_message(GuessNumber)
    def on_update_prompt(self, message=None):
        guess_str = '???' if self.guess is None else str(self.guess)
        self.gui.label.text = self.prompt.format(self.world, guess_str)

    def on_finish_game(self):
        self.gui.window.pop_handlers()

        if self.world.winner == self.id:
            self.gui.label.text = "You won!"
        else:
            self.gui.label.text = "You lost!"


class AiActor(kxg.Actor):
    """
    Wait a random amount of time, then guess a random number within the 
    remaining range.
    """

    def __init__(self):
        super().__init__()
        self.reset_timer()

    def on_update_game(self, dt):
        self.timer -= dt

        if self.timer < 0:
            lower_bound = self.world.lower_bound + 1
            upper_bound = self.world.upper_bound - 1
            guess = random.randint(lower_bound, upper_bound)
            self >> GuessNumber(self.id, guess)
            self.reset_timer()

    def reset_timer(self):
        self.timer = random.uniform(1, 3)



if __name__ == '__main__':
    kxg.quickstart.main(World, Referee, Gui, GuiActor, AiActor)
