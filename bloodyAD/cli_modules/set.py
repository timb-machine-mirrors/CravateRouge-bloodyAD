from bloodyAD import utils
from bloodyAD.utils import LOG
from bloodyAD.formatters import accesscontrol
from bloodyAD.network.ldap import Change
import msldap


def object(conn, target: str, attribute: str, v: list = []):
    """
    Add/Replace/Delete target's attribute

    :param target: sAMAccountName, DN, GUID or SID of the target
    :param attribute: name of the attribute
    :param v: add value if attribute doesn't exist, replace value if attribute exists, delete if no value given, can be called multiple times if multiple values to set (e.g -v HOST/janettePC -v HOST/janettePC.bloody.local)
    """
    print(v)
    conn.ldap.bloodymodify(target, {attribute: [(Change.REPLACE.value, v)]})
    LOG.info(f"[+] {target}'s {attribute} has been updated")


def owner(conn, target: str, owner: str):
    """
    Changes target ownership with provided owner (WriteOwner permission required)

    :param target: sAMAccountName, DN, GUID or SID of the target
    :param owner: sAMAccountName, DN, GUID or SID of the new owner
    """
    new_sid = next(conn.ldap.bloodysearch(owner, attr=["objectSid"]))["objectSid"]

    new_sd, _ = utils.getSD(
        conn, target, "nTSecurityDescriptor", accesscontrol.OWNER_SECURITY_INFORMATION
    )

    old_sid = new_sd["OwnerSid"].formatCanonical()
    if old_sid == new_sid:
        LOG.warning(f"[!] {old_sid} is already the owner, no modification will be made")
    else:
        new_sd["OwnerSid"].fromCanonical(new_sid)

        req_flags = msldap.wintypes.asn1.sdflagsrequest.SDFlagsRequestValue({
            "Flags": accesscontrol.OWNER_SECURITY_INFORMATION
        })
        controls = [("1.2.840.113556.1.4.801", True, req_flags.dump())]

        conn.ldap.bloodymodify(
            target,
            {"nTSecurityDescriptor": [(Change.REPLACE.value, new_sd.getData())]},
            controls,
        )

        LOG.info(f"[+] Old owner {old_sid} is now replaced by {owner} on {target}")


# Full info on what you can do:
# https://learn.microsoft.com/en-us/troubleshoot/windows-server/identity/change-windows-active-directory-user-password
def password(conn, target: str, newpass: str, oldpass: str = None):
    """
    Change password of a user/computer

    :param target: sAMAccountName, DN, GUID or SID of the target
    :param newpass: new password for the target
    :param oldpass: old password of the target, mandatory if you don't have "change password" permission on the target
    """
    encoded_new_password = '"%s"' % newpass
    if oldpass is not None:
        encoded_old_password = '"%s"' % oldpass
        op_list = [
            (Change.DELETE.value, encoded_old_password),
            (Change.ADD.value, encoded_new_password),
        ]
    else:
        op_list = [(Change.REPLACE.value, encoded_new_password)]

    # try:
    conn.ldap.bloodymodify(target, {"unicodePwd": op_list})
    # except ldap3.core.exceptions.LDAPConstraintViolationResult as e:
    #     error_str = (
    #         "If it's a user, double check new password fits password policy (don't"
    #         " forget password history and password change frequency!)"
    #     )
    #     if oldpass is not None:
    #         error_str += ", also ensure old password is valid"
    #     ldap3.core.exceptions.LDAPConstraintViolationResult.__str__ = (
    #         lambda self: error_str
    #     )

    #     raise e

    LOG.info("[+] Password changed successfully!")
    return True
