"""Every part of the database connection comes from the environment."""

import pytest

from app.db.connection import (
    DATABASE_VARIABLE,
    HOST_VARIABLE,
    PASSWORD_VARIABLE,
    PORT_VARIABLE,
    USER_VARIABLE,
    database_url,
)

VARIABLES = (
    USER_VARIABLE,
    PASSWORD_VARIABLE,
    HOST_VARIABLE,
    PORT_VARIABLE,
    DATABASE_VARIABLE,
)


@pytest.fixture()
def environment(monkeypatch) -> None:
    monkeypatch.setenv(USER_VARIABLE, "some-user")
    monkeypatch.setenv(PASSWORD_VARIABLE, "some-password")
    monkeypatch.setenv(HOST_VARIABLE, "some-host")
    monkeypatch.setenv(PORT_VARIABLE, "6543")
    monkeypatch.setenv(DATABASE_VARIABLE, "some-database")


def test_url_comes_from_the_environment(environment) -> None:
    url = database_url()

    assert url.username == "some-user"
    assert url.password == "some-password"
    assert url.host == "some-host"
    assert url.port == 6543
    assert url.database == "some-database"


@pytest.mark.parametrize("variable", VARIABLES)
def test_a_missing_variable_is_named(environment, monkeypatch, variable) -> None:
    monkeypatch.delenv(variable)

    with pytest.raises(RuntimeError, match=variable):
        database_url()


@pytest.mark.parametrize("variable", VARIABLES)
def test_an_empty_variable_counts_as_missing(
    environment, monkeypatch, variable
) -> None:
    monkeypatch.setenv(variable, "")

    with pytest.raises(RuntimeError, match=variable):
        database_url()


def test_a_port_that_is_no_number_is_refused(environment, monkeypatch) -> None:
    monkeypatch.setenv(PORT_VARIABLE, "five")

    with pytest.raises(RuntimeError, match=PORT_VARIABLE):
        database_url()
