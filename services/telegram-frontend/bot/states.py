# Uses PEP 8
# Tools: black, flake8, mypy

from aiogram.fsm.state import State, StatesGroup


class NewBooking(StatesGroup):
    """FSM steps for creating a new room booking request."""

    building = State()
    room = State()
    date = State()
    time_slot = State()
    purpose = State()
    title = State()
    confirm = State()


class Occupancy(StatesGroup):
    """FSM steps for viewing room occupancy on a given day."""

    room = State()
    date = State()


class BotLogin(StatesGroup):
    """FSM steps for email/password login inside the bot."""

    email = State()
    password = State()
