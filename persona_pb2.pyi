from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class IngestionRequest(_message.Message):
    __slots__ = ("text",)
    TEXT_FIELD_NUMBER: _ClassVar[int]
    text: str
    def __init__(self, text: _Optional[str] = ...) -> None: ...

class IngestionEvent(_message.Message):
    __slots__ = ("request_id", "s3_bucket", "s3_key")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    S3_BUCKET_FIELD_NUMBER: _ClassVar[int]
    S3_KEY_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    s3_bucket: str
    s3_key: str
    def __init__(self, request_id: _Optional[str] = ..., s3_bucket: _Optional[str] = ..., s3_key: _Optional[str] = ...) -> None: ...

class AnalysisFeatures(_message.Message):
    __slots__ = ("sentiment", "keywords", "word_count")
    SENTIMENT_FIELD_NUMBER: _ClassVar[int]
    KEYWORDS_FIELD_NUMBER: _ClassVar[int]
    WORD_COUNT_FIELD_NUMBER: _ClassVar[int]
    sentiment: str
    keywords: _containers.RepeatedScalarFieldContainer[str]
    word_count: int
    def __init__(self, sentiment: _Optional[str] = ..., keywords: _Optional[_Iterable[str]] = ..., word_count: _Optional[int] = ...) -> None: ...
