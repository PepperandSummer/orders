"""
Models for Order

All of the models are stored in this module
"""
import logging
from datetime import date
from abc import abstractmethod
# from enum import Enum
from flask_sqlalchemy import SQLAlchemy


logger = logging.getLogger("flask.app")

# Create the SQLAlchemy object to be initialized later in init_db()
db = SQLAlchemy()


# Function to initialize the database
def init_db(app):
    """ Initializes the SQLAlchemy app """
    Order.init_db(app)


class DataValidationError(Exception):
    """ Used for an data validation errors when deserializing """


class BaseModel:
    """
    A base class of data model that other order and Item models can inherit from
    """
    def __init__(self):
        self.id = None  # pylint: disable=invalid-name

    @abstractmethod
    def serialize(self):
        """ Convert an object to dictionary """

    @abstractmethod
    def deserialize(self, data):
        """ Convert a dictionary to an object """

    def create(self):
        """
        Creates a Order to the database
        """
        logger.info("Creating %s", self.id)
        self.id = None  # pylint: disable=invalid-name
        db.session.add(self)
        db.session.commit()

    def update(self):
        """
        Updates a Order to the database
        """
        logger.info("Saving %s", self.id)
        db.session.commit()

    def delete(self):
        """ Removes a Order from the data store """
        logger.info("Deleting %s", self.id)
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def init_db(cls, app):
        """ Initializes the database session """
        logger.info("Initializing database")
        cls.app = app
        # This is where we initialize SQLAlchemy from the Flask app
        db.init_app(app)
        app.app_context().push()
        db.create_all()  # make our sqlalchemy tables

    @classmethod
    def all(cls):
        """ Returns all of the Orders in the database """
        logger.info("Processing all Orders")
        return cls.query.all()

    @classmethod
    def find(cls, by_id):
        """ Finds a Order by it's ID """
        logger.info("Processing lookup for id %s ...", by_id)
        return cls.query.get(by_id)


##################################################
# Item MODEL
##################################################
class Item(db.Model, BaseModel):
    """
    A Class that represent Item Model
    """

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=False)
    order_id = db.Column(
        db.Integer, db.ForeignKey("order.id", ondelete="CASCADE"), nullable=False
    )

    def serialize(self) -> dict:
        """Serialize an Order into a dict"""
        return {
            "id": self.id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "total": self.total,
            "order_id": self.order_id,
        }

    def deserialize(self, data: dict):
        """
        Deserializes a Item from a dictionary
        Args:
            data (dict): A dictionary containing the Item data
        """
        try:
            self.product_id = data["product_id"]
            self.quantity = data["quantity"]
            if self.quantity < 1:
                raise DataValidationError("Invalid quantity detected in item product: "
                                          + str(data["quantity"]))
            self.total = data["total"]
        except AttributeError as error:
            raise DataValidationError("Invalid attribute: " + error.args[0]) from error
        except KeyError as error:
            raise DataValidationError("Invalid item: missing " + error.args[0]) from error
        except TypeError as error:
            raise DataValidationError(
                "Invalid item: body of request contained bad or no data " + str(error)
            ) from error
        return self


##################################################
# ORDER MODEL
##################################################
class Order(db.Model, BaseModel):
    """
    A Class that represent Order Model
    """
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date(), nullable=False, default=date.today())
    total = db.Column(db.Float, nullable=False)
    payment = db.Column(
        db.Enum("CREDITCARD", "DEBITCARD", "VEMO", name="payment_enum"),
        nullable=False
    )
    address = db.Column(db.String(100), nullable=False)
    customer_id = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.Enum("OPEN", "SHIPPING", "DELIVERED", "CANCELLED", name="status_enum"),
        nullable=False,
        server_default="OPEN"
    )
    items = db.relationship("Item", backref="order", passive_deletes=True)

    def __repr__(self):
        return f"<Order id=[{self.id}]>"

    def serialize(self) -> dict:
        """Serialize an Order into a dict"""
        order = {
            "id": self.id,
            "date": self.date.isoformat(),
            "total": self.total,
            "payment": self.payment,
            "address": self.address,
            "customer_id": self.customer_id,
            "status": self.status,
            "items": []
        }
        for product in self.items:
            order["items"].append(product.serialize())
        return order

    def deserialize(self, data: dict):
        """
        Deserializes an Order from a dictionary
        Args:
            data (dict): A dictionary containing the Order data
        """
        try:
            # assert(isinstance(data["total"],float), "total")
            self.total = data["total"]
            self.date = data["date"]
            self.payment = data.get("payment")
            self.address = data["address"]
            self.customer_id = data["customer_id"]
            self.status = data.get("status")
            items = data["items"]
            for json_product in items:
                product = Item()
                product.deserialize(json_product)
                self.items.append(product)
        except AttributeError as error:
            raise DataValidationError("Invalid attribute: " + error.args[0]) from error
        except KeyError as error:
            raise DataValidationError("Invalid order: missing " + error.args[0]) from error
        except TypeError as error:
            raise DataValidationError(
                "Invalid order: body of request contained bad or no data " + str(error)
            ) from error
        return self

    @classmethod
    def find_by_status(cls, status):
        """Returns all Orders with the given status """
        logger.info("Processing status query for %s ...", status)
        return cls.query.filter(cls.status == status)

    @classmethod
    def find_by_customer_id(cls, customer_id):
        """Returns all Orders with the given customer id"""
        logger.info("Processing customer id query for %s ...", customer_id)
        return cls.query.filter(cls.customer_id == customer_id)

    @classmethod
    def find_by_customer_id_and_status(cls, customer_id, status):
        """
        Find and return all orders for a given customer id and a specific order status.

        Args:
            customer_id: The id of the customer.
            status: The status of the orders to return.

        Returns:
            A list of orders that match the provided customer id and status.
        """
        logger.info("Processing customer-id and status query for %s and %s", customer_id, status)
        return cls.query.filter(cls.customer_id == customer_id, cls.status == status).all()
