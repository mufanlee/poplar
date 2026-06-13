from poplar.core.session import Message, Role, Session


def test_message_creation():
    msg = Message(role=Role.USER, content="Hello")
    assert msg.role == Role.USER
    assert msg.content == "Hello"


def test_message_to_dict():
    msg = Message(role=Role.USER, content="Test")
    d = msg.to_dict()
    assert d == {"role": "user", "content": "Test"}


def test_session_creation():
    session = Session(id="test-1", title="Test Session")
    assert session.id == "test-1"
    assert session.title == "Test Session"
    assert len(session.messages) == 0


def test_session_add_message():
    session = Session(id="test-1", title="Test")
    msg = Message(role=Role.USER, content="Hello")
    session.add_message(msg)
    assert len(session.messages) == 1
    assert session.messages[0].content == "Hello"
