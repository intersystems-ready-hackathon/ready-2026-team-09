/// Team 9's implementation of the Agent class, which defines the agent's behavior and capabilities.
Class Sample.Agent9 Extends %AI.Agent
{
    /// LLM Provider
    Parameter PROVIDER = "openai";

    /// LLM Model
    Parameter MODEL = "gpt-5-nano";

    /// Toolsets that the agent can use
    Parameter TOOLSETS = "Sample.ToolSet9";
    
    
    /// System Prompt
    XData INSTRUCTIONS [ MimeType = text/markdown ]
    {
    # IRIS Class Reference Assistant

    You are a helpful assistant with access to a set of tools to interact with the version-specific InterSystems IRIS Class Reference documentation. You can use these tools to look up information about classes, methods, properties, and other elements of the IRIS class library to help answer questions and provide guidance.

	You can also discover which versions of IRIS are supported by the documentation, and use that information to ensure that your answers are relevant to the user's version of IRIS.
    }

    Method %CreateProvider() As %Status {
        Set apiKey = $System.Util.GetEnviron("OPENAI_API_KEY")
        If apiKey = "" {
            Quit $$$ERROR($$$GeneralError, "OPENAI_API_KEY is not set")
        }

        Set sc = $$$OK
        Try {
            Set settings = {"api_key": (apiKey)}
            Set ..Provider = ##class(%AI.Provider).Create(..#PROVIDER, settings)
        } Catch ex {
            Set sc = $$$ERROR($$$GeneralError, "Failed to create provider '" _ ..#PROVIDER _ "': " _ ex.DisplayString())
        }

        If $$$ISERR(sc) Quit sc
        Quit $$$OK
    }


}
