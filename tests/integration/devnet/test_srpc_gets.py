#    Copyright 2022 Frank V. Castellucci
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#        http://www.apache.org/licenses/LICENSE-2.0
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# -*- coding: utf-8 -*-

"""Synchronous RPC testing."""


from pysui.sui import SuiClient, SuiRpcResult
from pysui.sui.sui_builders import GetCommittee, GetObject, GetPastObject
from pysui.sui.sui_types import (
    MoveDataDescriptor,
    ObjectNotExist,
    ObjectVersionTooHigh,
    SuiData,
    SuiGasDescriptor,
    SuiAddress,
    SuiGas,
    ObjectID,
)


def get_gas(client: SuiClient, for_address: SuiAddress = None) -> list[SuiGas]:
    """get_gas Utility func to refresh gas for address.

    :param client: _description_
    :type client: SuiClient
    :return: _description_
    :rtype: list[SuiGas]
    """
    result: SuiRpcResult = client.get_address_object_descriptors(SuiGasDescriptor, for_address)
    assert result.is_ok()
    ident_list = [desc.identifier for desc in result.result_data]
    result: SuiRpcResult = client.get_objects_for(ident_list)
    assert result.is_ok()
    return result.result_data


def get_data(client: SuiClient, for_address: SuiAddress = None) -> list[SuiData]:
    """get_data Fetch all data objects for address.

    :param client: Synchronous http client
    :type client: SuiClient
    :param for_address: Address to get objects for, defaults to None and uses active-address
    :type for_address: SuiAddress, optional
    :return: List of data objects owned by address, maybe empty
    :rtype: list[SuiData]
    """
    result: SuiRpcResult = client.get_address_object_descriptors(MoveDataDescriptor, for_address)
    assert result.is_ok()
    ident_list = [desc.identifier for desc in result.result_data]
    result: SuiRpcResult = client.get_objects_for(ident_list)
    assert result.is_ok()
    return result.result_data


def test_get_gas_activeaddress_pass(sui_client: SuiClient):
    """test_get_gasobjects_pass Fetch gas objects.

    Tests filtered descriptor fetch and convenience sui_getObject
    :param sui_client: Synchronous http client
    :type sui_client: SuiClient
    """
    gas_objects = get_gas(sui_client)
    assert len(gas_objects) > 3
    gas_balances = [gas.balance for gas in gas_objects]
    total_balance = sum(gas_balances)
    assert total_balance > 0


def test_get_gas_anyaddress_pass(sui_client: SuiClient):
    """test_get_gas_anyaddress_pass Check any other address has gas.

    :param sui_client: Synchronous http client
    :type sui_client: SuiClient
    :return: The unique non-active-address SuiAddress and it's gas objects or None if one does not exist
    :rtype: Union[SuiAddress, None]
    """
    active_address = sui_client.config.active_address
    addresses = set(sui_client.config.addresses)
    addresses.remove(active_address.identifier)
    for anyaddress in addresses:
        inaddr = SuiAddress.from_hex_string(anyaddress)
        gas_objects = get_gas(sui_client, inaddr)
        if gas_objects:
            gas_balances = [gas.balance for gas in gas_objects]
            total_balance = sum(gas_balances)
            assert total_balance > 0


def test_get_object_pass(sui_client: SuiClient):
    """test_get_object_pass Validate succesful fetch for details of gas object.

    :param sui_client: Synchronous http client
    :type sui_client: SuiClient
    """
    gas_objects = get_gas(sui_client)
    assert gas_objects
    # Convenience method on client
    gas_object = sui_client.get_object(gas_objects[0].identifier)
    assert gas_object
    assert gas_object.is_ok()
    # Builder approach
    builder = GetObject(gas_objects[0].identifier)
    gas_object2 = sui_client.execute(builder)
    assert gas_object2.is_ok()
    assert gas_object.result_data == gas_object2.result_data


def test_get_object_fail(sui_client: SuiClient):
    """test_get_object_fail Validate unsuccesful fetch of invalid ObjectID.

    :param sui_client: Synchronous http client
    :type sui_client: SuiClient
    """
    # Convenience method on client
    result = sui_client.get_object(ObjectID("0x09553"))
    assert isinstance(result.result_data, ObjectNotExist)


def test_get_past_object_pass(sui_client: SuiClient):
    """test_get_past_object_pass Validate succesful fetch for earlier version of gas object.

    :param sui_client: Synchronous http client
    :type sui_client: SuiClient
    """
    gas_objects = get_gas(sui_client)
    assert gas_objects
    multi_version = list(filter(lambda x: x.version > 1, gas_objects))
    assert multi_version
    builder = GetPastObject(multi_version[0].identifier, multi_version[0].version - 1)
    gas_object2 = sui_client.execute(builder)
    assert gas_object2
    assert gas_object2.result_data.version < multi_version[0].version
    assert gas_object2.result_data.balance > multi_version[0].balance


def test_get_past_object_fail(sui_client: SuiClient):
    """test_get_past_object_fail Validate unsuccesful fetch for version of object.

    :param sui_client: Synchronous http client
    :type sui_client: SuiClient
    """
    gas_objects = get_gas(sui_client)
    assert gas_objects
    multi_version = list(filter(lambda x: x.version > 1, gas_objects))
    assert multi_version
    builder = GetPastObject(multi_version[0].identifier, multi_version[0].version + 1)
    result = sui_client.execute(builder)
    assert isinstance(result.result_data, ObjectVersionTooHigh)


def test_committee(sui_client: SuiClient) -> None:
    """test_committee Expect 4 addresses with 1 staked_units each.

    :param sui_client: Synchronous http client
    :type sui_client: SuiClient
    """
    result = sui_client.execute(GetCommittee())
    assert result.is_ok()
    assert len(result.result_data.committee_info) == 4
    for committee in result.result_data.committee_info:
        assert committee.staked_units == 1
