"""
Utiilties for handling DB operations
"""

from fastapi import Depends
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from sqlmodel import create_engine, SQLModel, Session
from sqlmodel.sql._expression_select_cls import SelectOfScalar
import traceback
from typing import Annotated
from urllib.parse import urlparse, urlunparse

from app.helpers.conf import config
from app.helpers.exceptions import DBOperationException
from app.helpers.utils import get_secret


def prepare_url(url: str) -> str:
    """
    Prepares the MySQL connection string.

    Checks if the given connectin string has
    'mysql+pymysql' scheme, replaces the current
    scheme if not.

    The 'mysql+pymysql' scheme is required to
    indicate SQLAlchemy library to use the correct
    MySQL dialect(package).

    Args:
        url (str): The connection string from secrets.

    Returns:
        str: MySQL connection string with correct scheme.
    """
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme

    if "mysql+pymysql" != scheme:
        scheme = "mysql+pymysql"

    modified_parsed_url = parsed_url._replace(scheme=scheme)
    return urlunparse(modified_parsed_url)


MYSQL_CONNECTION_STRING = prepare_url(get_secret("pr-sandbox-mysql-connection-string"))
DB_ENGINE = create_engine(MYSQL_CONNECTION_STRING, echo=config.db_debug_logging)


class DBSession(Session):
    """
    Helper class to provide interface for common DB interactions.
    """

    def add_or_update(self, data_object: SQLModel):
        """
        Helper method to create or update an entry in DB

        Args:
            data_object (SQLModel): Object of a sub-class of SQLModel
        """
        try:
            self.add(data_object)
            self.commit()
        except Exception as ex:
            traceback.print_exc()
            raise DBOperationException(f"Exception while adding/updating a row - {ex}")

    def fetch_one(self, statement: SelectOfScalar) -> any:
        """
        Helper method to fetch a single entry from DB.

        Args:
            statement (SelectOfScalar): The SQLModel statement to be executed.

        Raises:
            DBOperationException: Any exception during db operations

        Returns:
            any: Query result as an object
        """
        try:
            return self.exec(statement).one()
        except NoResultFound:
            raise DBOperationException("No row was fetched for the given query")
        except MultipleResultsFound:
            raise DBOperationException(
                "Multiple matching rows found when one was expected"
            )
        except Exception as ex:
            traceback.print_exc()
            raise DBOperationException(f"Exception while fetching one row - {ex}")

    def fetch_all(self, statement: SelectOfScalar) -> any:
        """
        Helper method to fetch all entries from DB.

        Args:
            statement (SelectOfScalar): The SQLModel statement to be executed.

        Raises:
            DBOperationException: Any exception during db operations

        Returns:
            Sequence: Query result as a sequece of object.
        """
        try:
            return self.exec(statement).all()
        except Exception as ex:
            traceback.print_exc()
            raise DBOperationException(f"Exception while fetching rows - {ex}")


def get_session():
    with DBSession(DB_ENGINE) as session:
        yield session


SessionDep = Annotated[DBSession, Depends(get_session)]
