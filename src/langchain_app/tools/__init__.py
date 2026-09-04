"""LangChain tools package (business_tools + retrieval_tool).

Import-order-sensitive on Windows. `retrieval_tool` -> `vectorstore.store`
-> `vectorstore.embeddings` lazily loads `sentence-transformers` (torch) -
only when an embedding is actually computed, not at import time - while
`business_tools` -> `database.dao` -> `database.connection.connection_pool`
eagerly loads SQLAlchemy's compiled Cython extensions
(`sqlalchemy.cyextension.*`) at import time. If those load into the
process before torch does, torch's own DLL loading then fails:

    OSError: [WinError 1114] ... c10.dll ...

Same category of issue as the documented torch-vs-onnxruntime DLL
load-order quirk (see the plan doc's "lessons learned"), different
pairing (torch vs. SQLAlchemy's cyextensions), found while wiring
business_tools and retrieval_tool into the same process for the first
time. Forcing the embedding model to load here, at this package's import
time - before Python can get to the `business_tools` submodule (and
therefore SQLAlchemy) - fixes it, since importing any submodule of a
package always runs the package's `__init__.py` first.

Anything that needs both `database.dao` and this package in the same
process should import `langchain_app.tools` (or a name from it) before
importing `database.dao` directly, so this guard runs first.
"""

from langchain_app.vectorstore.embeddings import get_embeddings

get_embeddings()  # force torch to load before a sibling import can pull in SQLAlchemy
