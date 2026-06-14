from poplar.core.session import Message, Role, Session


def test_message_creation():
    msg = Message(role=Role.USER, content="Hello")
    assert msg.role == Role.USER
    assert msg.content == "Hello"
    assert msg.tool_calls is None
    assert msg.tool_call_id is None


def test_message_to_dict():
    msg = Message(role=Role.USER, content="Test")
    d = msg.to_dict()
    assert d == {"role": "user", "content": "Test"}


def test_message_with_tool_calls():
    msg = Message(role=Role.ASSISTANT, content=None, tool_calls=[
        {"id": "call_1", "type": "function", "function": {"name": "read_file", "arguments": '{"path":"/tmp"}'}}
    ])
    d = msg.to_dict()
    assert d["role"] == "assistant"
    assert d["content"] is None
    assert len(d["tool_calls"]) == 1
    assert d["tool_calls"][0]["function"]["name"] == "read_file"


def test_tool_message():
    msg = Message(role=Role.TOOL, content="file contents", tool_call_id="call_1", name="read_file")
    d = msg.to_dict()
    assert d["role"] == "tool"
    assert d["content"] == "file contents"
    assert d["tool_call_id"] == "call_1"
    assert d["name"] == "read_file"


def test_empty_content_to_dict():
    msg = Message(role=Role.ASSISTANT, content="")
    d = msg.to_dict()
    assert d["content"] == ""


def test_to_dict_always_has_content():
    msg = Message(role=Role.TOOL, tool_call_id="x", name="test")
    d = msg.to_dict()
    assert "content" in d
    assert "tool_call_id" in d


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


def test_get_messages_for_api():
    session = Session(id="test-1", title="Test")
    session.add_message(Message(role=Role.USER, content="hi"))
    session.add_message(Message(role=Role.ASSISTANT, content="hello", tool_calls=[
        {"id": "c1", "type": "function", "function": {"name": "f", "arguments": "{}"}}
    ]))
    session.add_message(Message(role=Role.TOOL, content="result", tool_call_id="c1", name="f"))
    msgs = session.get_messages_for_api()
    assert len(msgs) == 3
    assert msgs[0]["role"] == "user"
    assert msgs[1]["tool_calls"] is not None
    assert msgs[2]["role"] == "tool"
    assert msgs[2]["tool_call_id"] == "c1"
