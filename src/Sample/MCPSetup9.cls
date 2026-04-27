Class Sample.MCPSetup9 Extends %RegisteredObject
{   
    /// Sample code to set up an MCP Application
    ClassMethod Run() As %Status
    {   
        New $NAMESPACE
        Set $NAMESPACE = "%SYS"
        set sc =  ##class(Security.Applications).Delete("/mcp/sample9")
        kill props
        set props("DispatchClass") = "Sample.MCPService9" 
        set props("AutheEnabled") = 64 // Unautheticated access
        set props("Type") = 18 // Type 18 corresponds to MCP service, ensuring it lives in the MCP Service menu. 
        set props("NameSpace") = "IRISAPP"
        set props("MatchRoles") = ":%All"
        set sc =  ##class(Security.Applications).Create("/mcp/sample9", .props)
        if $$$ISERR(sc) {
            write "Error creating MCP Service: ", $SYSTEM.Status.GetErrorText(sc), !
            quit sc
        } else {
            write "MCP Service created successfully.", !
            quit $$$OK
        }
    }
}